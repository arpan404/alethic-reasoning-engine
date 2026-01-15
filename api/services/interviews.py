"""Interview service functions."""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.interviews import Interview, InterviewStatus, InterviewType
from database.models.applications import Application, ApplicationActivity, ApplicationActivityType
from database.models.users import User

logger = logging.getLogger(__name__)


async def schedule_interview(
    application_id: int,
    interview_type: str,
    scheduled_at: datetime,
    duration_minutes: int = 60,
    interviewer_ids: Optional[List[int]] = None,
    location: Optional[str] = None,
    notes: Optional[str] = None,
    scheduled_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Schedule an interview."""
    async with AsyncSessionLocal() as session:
        app_result = await session.execute(
            select(Application).where(Application.id == application_id)
        )
        application = app_result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
        
        try:
            interview_type_enum = InterviewType(interview_type)
        except ValueError:
            interview_type_enum = InterviewType.PHONE_SCREEN
        
        interview = Interview(
            application_id=application_id,
            job_id=application.job_id,
            interview_type=interview_type_enum,
            status=InterviewStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            location=location,
            notes=notes,
            scheduled_by_id=scheduled_by,
        )
        session.add(interview)
        await session.flush()
        
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.INTERVIEW_SCHEDULED,
            performed_by_id=scheduled_by,
            details={
                "interview_id": interview.id,
                "interview_type": interview_type,
                "scheduled_at": scheduled_at.isoformat(),
            },
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "interview_id": interview.id,
            "application_id": application_id,
            "interview_type": interview_type,
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": duration_minutes,
            "status": "scheduled",
        }


async def list_interviews(
    application_id: Optional[int] = None,
    job_id: Optional[int] = None,
    interviewer_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List interviews with filtering."""
    async with AsyncSessionLocal() as session:
        query = select(Interview).options(
            selectinload(Interview.application).selectinload(Application.candidate)
        )
        
        if application_id:
            query = query.where(Interview.application_id == application_id)
        if job_id:
            query = query.where(Interview.job_id == job_id)
        if status:
            try:
                status_enum = InterviewStatus(status)
                query = query.where(Interview.status == status_enum)
            except ValueError:
                pass
        if start_date:
            query = query.where(Interview.scheduled_at >= start_date)
        if end_date:
            query = query.where(Interview.scheduled_at <= end_date)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Interview.scheduled_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        interviews = result.scalars().all()
        
        interview_list = []
        for interview in interviews:
            candidate_name = None
            if interview.application and interview.application.candidate:
                c = interview.application.candidate
                candidate_name = f"{c.first_name} {c.last_name}"
            
            interview_list.append({
                "id": interview.id,
                "application_id": interview.application_id,
                "candidate_name": candidate_name,
                "interview_type": interview.interview_type.value if hasattr(interview.interview_type, 'value') else str(interview.interview_type),
                "status": interview.status.value if hasattr(interview.status, 'value') else str(interview.status),
                "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
                "duration_minutes": interview.duration_minutes,
                "location": interview.location,
            })
        
        return {
            "interviews": interview_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def get_interview(interview_id: int) -> Optional[Dict[str, Any]]:
    """Get interview details."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Interview)
            .options(
                selectinload(Interview.application).selectinload(Application.candidate)
            )
            .where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        
        if not interview:
            return None
        
        candidate_name = None
        if interview.application and interview.application.candidate:
            c = interview.application.candidate
            candidate_name = f"{c.first_name} {c.last_name}"
        
        return {
            "id": interview.id,
            "application_id": interview.application_id,
            "job_id": interview.job_id,
            "candidate_name": candidate_name,
            "interview_type": interview.interview_type.value if hasattr(interview.interview_type, 'value') else str(interview.interview_type),
            "status": interview.status.value if hasattr(interview.status, 'value') else str(interview.status),
            "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
            "duration_minutes": interview.duration_minutes,
            "location": interview.location,
            "notes": interview.notes,
            "created_at": interview.created_at.isoformat() if interview.created_at else None,
        }


async def cancel_interview(
    interview_id: int,
    reason: Optional[str] = None,
    cancelled_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Cancel an interview."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        
        if not interview:
            return {"success": False, "error": "Interview not found"}
        
        if interview.status == InterviewStatus.CANCELLED:
            return {"success": False, "error": "Interview is already cancelled"}
        
        interview.status = InterviewStatus.CANCELLED
        interview.cancellation_reason = reason
        
        activity = ApplicationActivity(
            application_id=interview.application_id,
            activity_type=ApplicationActivityType.INTERVIEW_CANCELLED,
            performed_by_id=cancelled_by,
            details={"interview_id": interview_id, "reason": reason},
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "interview_id": interview_id,
            "status": "cancelled",
        }


async def reschedule_interview(
    interview_id: int,
    new_datetime: datetime,
    reason: Optional[str] = None,
    rescheduled_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Reschedule an interview."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Interview).where(Interview.id == interview_id)
        )
        interview = result.scalar_one_or_none()
        
        if not interview:
            return {"success": False, "error": "Interview not found"}
        
        old_datetime = interview.scheduled_at
        interview.scheduled_at = new_datetime
        interview.status = InterviewStatus.RESCHEDULED
        
        activity = ApplicationActivity(
            application_id=interview.application_id,
            activity_type=ApplicationActivityType.INTERVIEW_RESCHEDULED,
            performed_by_id=rescheduled_by,
            details={
                "interview_id": interview_id,
                "old_datetime": old_datetime.isoformat() if old_datetime else None,
                "new_datetime": new_datetime.isoformat(),
                "reason": reason,
            },
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "interview_id": interview_id,
            "old_datetime": old_datetime.isoformat() if old_datetime else None,
            "new_datetime": new_datetime.isoformat(),
            "status": "rescheduled",
        }
