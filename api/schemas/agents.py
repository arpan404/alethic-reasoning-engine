from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's message to the agent")
    session_id: str = Field(..., description="Unique session identifier for the conversation")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context for the agent")

class ToolOutput(BaseModel):
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: Any

class AgentResponse(BaseModel):
    text: str = Field(..., description="The agent's text response")
    tools_used: List[ToolOutput] = Field(default=[], description="List of tools used during generation")
    sources: List[str] = Field(default=[], description="List of sources cited")

class ResumeParseResponse(BaseModel):
    success: bool
    parsed_data: Dict[str, Any]
    error: Optional[str] = None

class EvaluationRequest(BaseModel):
    application_id: int
    type: str = Field(..., pattern="^(pre|full)$", description="Type of evaluation: 'pre' or 'full'")

class EvaluationResponse(BaseModel):
    success: bool
    task_id: str
    message: str

class InterviewQuestionsRequest(BaseModel):
    application_id: int
    interview_type: str = Field(default="general", description="Type of interview")
    focus_areas: List[str] = Field(default=[], description="Specific areas to focus questions on")

class InterviewQuestionsResponse(BaseModel):
    questions: List[str]
    context: Optional[str] = None
