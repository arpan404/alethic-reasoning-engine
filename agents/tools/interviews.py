"""Interview management tools for Alethic agents.

These tools provide database operations and scheduling functionality
for managing interviews, including scheduling, retrieval, and analysis.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import select, and_, desc, or_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.ai_evaluations import (
    Interview,
    InterviewStatus,
    InterviewType,
    MeetingPlatform,
    InterviewFeedback,
)
from database.models.applications import Application

logger = logging.getLogger(__name__)


async def schedule_interview(
    application_id: int,
    interview_type: str,
    scheduled_at: datetime,
    duration_minutes: int = 60,
    interviewers: List[int] = None,
    platform: str = "zoom",
    location: Optional[str] = None,
    notes: Optional[str] = None,
    scheduled_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Schedule an interview for an application.
    
    Args:
        application_id: The application to schedule interview for
        interview_type: Type of interview (initial_screening, phone_screen, technical, 
                        behavioral, cultural, case_study, panel, final, offer_discussion)
        scheduled_at: Interview datetime
        duration_minutes: Duration in minutes
        interviewers: List of interviewer user IDs
        platform: Meeting platform (zoom, google_meet, microsoft_teams, phone, in_person)
        location: Physical location (for in-person interviews)
        notes: Optional notes about the interview
        scheduled_by: User ID who is scheduling
        
    Returns:
        Dictionary with interview details and meeting link
    """
    # Validate interview type
    valid_types = [t.value for t in InterviewType]
    if interview_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid interview type '{interview_type}'. Valid options: {valid_types}",
        }
    
    # Validate platform
    valid_platforms = [p.value for p in MeetingPlatform]
    if platform not in valid_platforms:
        return {
            "success": False,
            "error": f"Invalid platform '{platform}'. Valid options: {valid_platforms}",
        }
    
    async with AsyncSessionLocal() as session:
        # Verify application exists
        app_query = (
            select(Application)
            .options(selectinload(Application.candidate), selectinload(Application.job))
            .where(Application.id == application_id)
        )
        result = await session.execute(app_query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        # Check for scheduling conflicts
        end_time = scheduled_at + timedelta(minutes=duration_minutes)
        conflict_query = select(Interview).where(
            and_(
                Interview.application_id == application_id,
                Interview.status.in_(["scheduled", "confirmed"]),
                or_(
                    and_(
                        Interview.scheduled_at <= scheduled_at,
                        Interview.scheduled_end_at > scheduled_at,
                    ),
                    and_(
                        Interview.scheduled_at < end_time,
                        Interview.scheduled_end_at >= end_time,
                    ),
                ),
            )
        )
        conflict_result = await session.execute(conflict_query)
        conflicts = conflict_result.scalars().all()
        
        if conflicts:
            return {
                "success": False,
                "error": "Time slot conflicts with existing interview",
                "conflicting_interview_id": conflicts[0].id,
            }
        
        # Create interview
        interview = Interview(
            application_id=application_id,
            candidate_id=app.candidate_id,
            job_id=app.job_id,
            interview_type=interview_type,
            status=InterviewStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            scheduled_end_at=end_time,
            duration_minutes=duration_minutes,
            platform=platform,
            location=location,
            notes=notes,
            created_by=scheduled_by,
        )
        session.add(interview)
        await session.commit()
        await session.refresh(interview)
        
        candidate_name = ""
        if app.candidate:
            candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
        
        logger.info(
            f"Scheduled {interview_type} interview for application {application_id} "
            f"at {scheduled_at.isoformat()}"
        )
        
        # Queue calendar event creation and invites
        from agents.tools.queue import enqueue_task
        await enqueue_task(
            task_type="create_interview_calendar_event",
            payload={
                "interview_id": interview.id,
                "application_id": application_id,
                "interviewers": interviewers or [],
            },
        )
        
        return {
            "success": True,
            "interview_id": interview.id,
            "application_id": application_id,
            "candidate_name": candidate_name,
            "interview_type": interview_type,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": duration_minutes,
            "platform": platform,
            "status": "scheduled",
            "message": "Interview scheduled. Calendar invites will be sent shortly.",
        }


async def get_interview_schedule(
    application_id: Optional[int] = None,
    job_id: Optional[int] = None,
    interviewer_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """Get interview schedule with optional filtering.
    
    Args:
        application_id: Filter by application
        job_id: Filter by job
        interviewer_id: Filter by interviewer
        start_date: Filter interviews starting after this date
        end_date: Filter interviews starting before this date
        status: Filter by status
        
    Returns:
        Dictionary with list of scheduled interviews
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Interview)
            .options(
                selectinload(Interview.application).selectinload(Application.candidate),
            )
        )
        conditions = []
        
        if application_id:
            conditions.append(Interview.application_id == application_id)
        
        if job_id:
            conditions.append(Interview.job_id == job_id)
        
        if start_date:
            conditions.append(Interview.scheduled_at >= start_date)
        
        if end_date:
            conditions.append(Interview.scheduled_at <= end_date)
        
        if status:
            conditions.append(Interview.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Interview.scheduled_at)
        
        result = await session.execute(query)
        interviews = result.scalars().all()
        
        schedule = []
        for interview in interviews:
            candidate_name = ""
            if interview.application and interview.application.candidate:
                c = interview.application.candidate
                candidate_name = f"{c.first_name} {c.last_name}".strip()
            
            schedule.append({
                "id": interview.id,
                "application_id": interview.application_id,
                "candidate_name": candidate_name,
                "interview_type": interview.interview_type,
                "status": interview.status,
                "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
                "scheduled_end_at": interview.scheduled_end_at.isoformat() if interview.scheduled_end_at else None,
                "duration_minutes": interview.duration_minutes,
                "platform": interview.platform,
                "location": interview.location,
                "meeting_link": interview.meeting_link,
            })
        
        return {
            "interviews": schedule,
            "total": len(schedule),
        }


async def get_interview_analysis(interview_id: int) -> Optional[Dict[str, Any]]:
    """Get AI analysis results for a completed interview.
    
    Args:
        interview_id: The interview ID
        
    Returns:
        Dictionary containing interview analysis and feedback, or None if not found
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Interview)
            .options(
                selectinload(Interview.feedback),
                selectinload(Interview.transcript_analysis),
                selectinload(Interview.application).selectinload(Application.candidate),
            )
            .where(Interview.id == interview_id)
        )
        result = await session.execute(query)
        interview = result.scalar_one_or_none()
        
        if not interview:
            return None
        
        candidate_name = ""
        if interview.application and interview.application.candidate:
            c = interview.application.candidate
            candidate_name = f"{c.first_name} {c.last_name}".strip()
        
        # Collect feedback from all interviewers
        feedback_list = []
        for fb in (interview.feedback or []):
            feedback_list.append({
                "interviewer_id": fb.interviewer_id,
                "recommendation": fb.recommendation,
                "overall_rating": fb.overall_rating,
                "technical_rating": fb.technical_rating,
                "communication_rating": fb.communication_rating,
                "cultural_fit_rating": fb.cultural_fit_rating,
                "strengths": fb.strengths or [],
                "concerns": fb.concerns or [],
                "notes": fb.notes,
                "submitted_at": fb.created_at.isoformat() if fb.created_at else None,
            })
        
        # AI transcript analysis if available
        ai_analysis = None
        if interview.transcript_analysis:
            ta = interview.transcript_analysis
            ai_analysis = {
                "summary": ta.summary,
                "key_topics_discussed": ta.key_topics or [],
                "candidate_strengths": ta.candidate_strengths or [],
                "candidate_concerns": ta.candidate_concerns or [],
                "follow_up_questions": ta.follow_up_questions or [],
                "sentiment_score": ta.sentiment_score,
                "confidence_score": ta.confidence_score,
            }
        
        return {
            "interview_id": interview_id,
            "application_id": interview.application_id,
            "candidate_name": candidate_name,
            "interview_type": interview.interview_type,
            "status": interview.status,
            "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
            "actual_duration_minutes": interview.actual_duration_minutes,
            "feedback": feedback_list,
            "ai_analysis": ai_analysis,
            "recording_available": interview.recording_url is not None,
            "transcript_available": interview.transcript_url is not None,
        }


async def generate_interview_questions(
    application_id: int,
    interview_type: str,
    focus_areas: Optional[List[str]] = None,
    include_gaps: bool = True,
) -> Dict[str, Any]:
    """Queue generation of tailored interview questions for a candidate.
    
    The LLM will generate questions based on:
    - Candidate profile and resume
    - Job requirements
    - Evaluation gaps to explore
    - Specified focus areas
    
    Args:
        application_id: The application to generate questions for
        interview_type: Type of interview (technical, behavioral, cultural, etc.)
        focus_areas: Optional specific areas to focus questions on
        include_gaps: Whether to include questions about evaluation gaps
        
    Returns:
        Dictionary with task_id for the generation job
    """
    # Verify application exists
    async with AsyncSessionLocal() as session:
        query = select(Application).where(Application.id == application_id)
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
    
    # Queue the question generation task
    from agents.tools.queue import enqueue_task
    task_result = await enqueue_task(
        task_type="generate_interview_questions",
        payload={
            "application_id": application_id,
            "interview_type": interview_type,
            "focus_areas": focus_areas or [],
            "include_gaps": include_gaps,
        },
        priority="high",
    )
    
    logger.info(
        f"Queued interview question generation for application {application_id} "
        f"({interview_type})"
    )
    
    return {
        "success": True,
        "application_id": application_id,
        "interview_type": interview_type,
        "task_id": task_result.get("task_id"),
        "message": "Interview questions are being generated. Results will be available shortly.",
    }
