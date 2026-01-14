"""Communication tools for Alethic agents.

These tools handle candidate communications including
emails, notifications, and message history.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.communications import (
    EmailTemplate,
    EmailLog,
    CommunicationHistory,
)
from database.models.applications import Application

logger = logging.getLogger(__name__)


async def send_rejection_email(
    application_id: int,
    template_id: Optional[int] = None,
    custom_message: Optional[str] = None,
    send_immediately: bool = True,
    sent_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Send a rejection email to a candidate.
    
    Args:
        application_id: The application to send rejection for
        template_id: Optional email template to use
        custom_message: Optional custom message to include
        send_immediately: Whether to send now or queue for later
        sent_by: User ID who is sending
        
    Returns:
        Dictionary with send status and message details
    """
    async with AsyncSessionLocal() as session:
        # Get application with candidate info
        query = (
            select(Application)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.job),
            )
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        if not app.candidate or not app.candidate.email:
            return {
                "success": False,
                "error": "Candidate email not found",
            }
        
        candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
        candidate_email = app.candidate.email
        job_title = app.job.title if app.job else "the position"
        
        # Get template if specified
        template_content = None
        template_subject = "Update on Your Application"
        if template_id:
            template_query = select(EmailTemplate).where(EmailTemplate.id == template_id)
            template_result = await session.execute(template_query)
            template = template_result.scalar_one_or_none()
            if template:
                template_content = template.body
                template_subject = template.subject
    
    # Queue the email
    from agents.tools.queue import enqueue_task
    task_result = await enqueue_task(
        task_type="send_email",
        payload={
            "to": candidate_email,
            "to_name": candidate_name,
            "subject": template_subject,
            "template_id": template_id,
            "template_content": template_content,
            "custom_message": custom_message,
            "email_type": "rejection",
            "application_id": application_id,
            "variables": {
                "candidate_name": candidate_name,
                "candidate_first_name": app.candidate.first_name if app.candidate else "",
                "job_title": job_title,
            },
            "sent_by": sent_by,
            "send_immediately": send_immediately,
        },
        priority="normal",
    )
    
    logger.info(
        f"Queued rejection email for application {application_id} "
        f"to {candidate_email}"
    )
    
    return {
        "success": True,
        "application_id": application_id,
        "candidate_email": candidate_email,
        "candidate_name": candidate_name,
        "task_id": task_result.get("task_id"),
        "message": "Rejection email has been queued" + (
            " and will be sent shortly" if send_immediately else " for scheduled sending"
        ),
    }


async def send_interview_invitation(
    application_id: int,
    interview_id: int,
    template_id: Optional[int] = None,
    custom_message: Optional[str] = None,
    sent_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Send an interview invitation to a candidate.
    
    Args:
        application_id: The application
        interview_id: The scheduled interview
        template_id: Optional email template to use
        custom_message: Optional custom message to include
        sent_by: User ID who is sending
        
    Returns:
        Dictionary with send status
    """
    from database.models.ai_evaluations import Interview
    
    async with AsyncSessionLocal() as session:
        # Get application and interview
        app_query = (
            select(Application)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.job),
            )
            .where(Application.id == application_id)
        )
        app_result = await session.execute(app_query)
        app = app_result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        interview_query = select(Interview).where(Interview.id == interview_id)
        interview_result = await session.execute(interview_query)
        interview = interview_result.scalar_one_or_none()
        
        if not interview:
            return {
                "success": False,
                "error": f"Interview with ID {interview_id} not found",
            }
        
        if not app.candidate or not app.candidate.email:
            return {
                "success": False,
                "error": "Candidate email not found",
            }
        
        candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
        candidate_email = app.candidate.email
        job_title = app.job.title if app.job else "the position"
    
    # Queue the email
    from agents.tools.queue import enqueue_task
    task_result = await enqueue_task(
        task_type="send_email",
        payload={
            "to": candidate_email,
            "to_name": candidate_name,
            "subject": f"Interview Invitation - {job_title}",
            "template_id": template_id,
            "custom_message": custom_message,
            "email_type": "interview_invitation",
            "application_id": application_id,
            "interview_id": interview_id,
            "variables": {
                "candidate_name": candidate_name,
                "candidate_first_name": app.candidate.first_name if app.candidate else "",
                "job_title": job_title,
                "interview_type": interview.interview_type,
                "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else "",
                "duration_minutes": interview.duration_minutes,
                "platform": interview.platform,
                "meeting_link": interview.meeting_link or "",
                "location": interview.location or "",
            },
            "sent_by": sent_by,
            "send_immediately": True,
        },
        priority="high",
    )
    
    logger.info(
        f"Queued interview invitation for application {application_id} "
        f"interview {interview_id} to {candidate_email}"
    )
    
    return {
        "success": True,
        "application_id": application_id,
        "interview_id": interview_id,
        "candidate_email": candidate_email,
        "candidate_name": candidate_name,
        "task_id": task_result.get("task_id"),
        "message": "Interview invitation has been queued and will be sent shortly",
    }


async def get_email_templates(
    organization_id: int,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Get available email templates for an organization.
    
    Args:
        organization_id: The organization ID
        category: Optional filter by category (rejection, interview, offer, etc.)
        
    Returns:
        Dictionary with list of templates
    """
    async with AsyncSessionLocal() as session:
        query = select(EmailTemplate).where(
            EmailTemplate.organization_id == organization_id
        )
        
        if category:
            query = query.where(EmailTemplate.category == category)
        
        query = query.order_by(EmailTemplate.name)
        
        result = await session.execute(query)
        templates = result.scalars().all()
        
        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category,
                    "subject": t.subject,
                    "description": t.description,
                    "is_default": t.is_default,
                    "variables": t.variables or [],
                }
                for t in templates
            ],
            "total": len(templates),
        }


async def get_communication_history(
    application_id: int,
    limit: int = 50,
) -> Dict[str, Any]:
    """Get communication history for an application.
    
    Args:
        application_id: The application ID
        limit: Maximum number of records to return
        
    Returns:
        Dictionary with chronological communication history
    """
    async with AsyncSessionLocal() as session:
        # Get email logs
        email_query = (
            select(EmailLog)
            .where(EmailLog.application_id == application_id)
            .order_by(desc(EmailLog.sent_at))
            .limit(limit)
        )
        email_result = await session.execute(email_query)
        emails = email_result.scalars().all()
        
        # Get general communication history
        comm_query = (
            select(CommunicationHistory)
            .where(CommunicationHistory.application_id == application_id)
            .order_by(desc(CommunicationHistory.created_at))
            .limit(limit)
        )
        comm_result = await session.execute(comm_query)
        communications = comm_result.scalars().all()
        
        history = []
        
        for email in emails:
            history.append({
                "type": "email",
                "direction": "outbound",
                "subject": email.subject,
                "to": email.to_email,
                "email_type": email.email_type,
                "status": email.status,
                "sent_at": email.sent_at.isoformat() if email.sent_at else None,
                "opened_at": email.opened_at.isoformat() if email.opened_at else None,
                "clicked_at": email.clicked_at.isoformat() if email.clicked_at else None,
            })
        
        for comm in communications:
            history.append({
                "type": comm.communication_type,
                "direction": comm.direction,
                "subject": comm.subject,
                "summary": comm.summary,
                "channel": comm.channel,
                "status": comm.status,
                "created_at": comm.created_at.isoformat() if comm.created_at else None,
            })
        
        # Sort by date descending
        history.sort(
            key=lambda x: x.get("sent_at") or x.get("created_at") or "",
            reverse=True
        )
        
        return {
            "application_id": application_id,
            "history": history[:limit],
            "total": len(history),
        }
