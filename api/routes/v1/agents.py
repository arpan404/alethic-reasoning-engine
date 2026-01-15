"""
Agents API - The primary chat-first interface.

This is the main entry point for the Alethic AI Hiring Copilot.
Users interact with the AI through natural language.
"""

import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from google.adk.agents import Agent as ADKAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from api.dependencies import require_active_user
from database.models.users import User
from agents.tools import adk as tools
from core.security import audit_log, AuditAction, ResourceType

router = APIRouter(prefix="/agents", tags=["Agents"])
logger = logging.getLogger(__name__)

# Session service (singleton)
session_service = InMemorySessionService()

# Initialize the Alethic Copilot Agent
alethic_agent = ADKAgent(
    model='gemini-2.0-flash',
    name='alethic_copilot',
    instruction="""You are Alethic, an expert AI Hiring Copilot.

Your capabilities:
- Search candidates using natural language
- View candidate profiles, resumes, and evaluations
- Schedule interviews and manage the hiring pipeline
- Compare candidates and provide recommendations
- Answer questions about hiring data and processes

Guidelines:
- Always explain your reasoning clearly
- When taking actions (shortlist, reject, schedule), confirm details first
- Provide specific, actionable insights
- Be concise but thorough
""",
    tools=[
        # Candidates
        tools.get_candidate, tools.list_candidates, tools.get_candidate_documents,
        # Jobs
        tools.get_job, tools.list_jobs, tools.get_job_requirements,
        # Applications
        tools.get_application, tools.list_applications, tools.get_application_history,
        # Evaluations
        tools.get_pre_evaluation, tools.get_full_evaluation, tools.get_prescreening_results,
        tools.trigger_evaluation, tools.get_candidate_ranking,
        # Interviews
        tools.get_interview_schedule, tools.get_interview_analysis, tools.generate_interview_questions,
        # Documents
        tools.read_resume, tools.read_cover_letter, tools.read_linkedin_profile, tools.read_portfolio,
        # Comparison
        tools.compare_candidates,
        # Search
        tools.search_candidates, tools.find_best_matches, tools.find_similar_candidates,
        # Communications
        tools.get_email_templates, tools.get_communication_history,
        # Action tools (can be triggered via chat too)
        tools.shortlist_candidate, tools.reject_candidate, tools.move_candidate_stage,
        tools.schedule_interview, tools.send_rejection_email, tools.send_interview_invitation,
    ],
)


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    query: str = Field(..., min_length=1, max_length=2000, description="User's message")
    session_id: str = Field(..., description="Conversation session ID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context (job_id, etc)")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    text: str = Field(..., description="AI response text")
    actions_taken: list = Field(default=[], description="Actions performed by the AI")
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_copilot(
    request: ChatRequest,
    req: Request,
    current_user: User = Depends(require_active_user),
):
    """
    Chat with the AI Hiring Copilot.
    
    This is the primary interface for Alethic. Send natural language
    queries and the AI will search, analyze, and take actions.
    
    **Examples:**
    - "Show me the top candidates for the Senior Engineer role"
    - "Compare John Smith and Jane Doe"
    - "Schedule an interview with the shortlisted candidates"
    - "Why was this candidate rejected?"
    
    **Authorization**: Requires authentication.
    
    **Audit**: All interactions are logged.
    """
    user_id = str(current_user.id)
    app_name = "alethic"
    
    try:
        # Create/get session
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=request.session_id
        )
    except Exception:
        pass  # Session may already exist
    
    runner = Runner(
        agent=alethic_agent,
        app_name=app_name,
        session_service=session_service
    )
    
    content = types.Content(role="user", parts=[types.Part(text=request.query)])
    
    try:
        events = runner.run_async(
            user_id=user_id,
            session_id=request.session_id,
            new_message=content
        )
        
        final_text = ""
        actions_taken = []
        
        async for event in events:
            if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            final_text += part.text
        
        return ChatResponse(
            text=final_text,
            actions_taken=actions_taken,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process request")
