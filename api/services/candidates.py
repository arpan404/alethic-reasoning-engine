"""Candidate service functions."""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.candidates import Candidate
from database.models.applications import Application, ApplicationActivity, ApplicationActivityType
from database.models.jobs import Job
from database.models.files import File

logger = logging.getLogger(__name__)


async def get_candidate(application_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed candidate information via application ID."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.job),
            )
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application or not application.candidate:
            return None
            
        candidate = application.candidate
        job = application.job
        
        return {
            "id": candidate.id,
            "application_id": application.id,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "linkedin_url": candidate.linkedin_url,
            "portfolio_url": candidate.portfolio_url,
            "experience_years": candidate.experience_years,
            "current_title": candidate.current_title,
            "current_company": candidate.current_company,
            "skills": candidate.skills or [],
            "education": candidate.education or [],
            "work_history": candidate.work_history or [],
            "application": {
                "id": application.id,
                "status": application.status,
                "stage": application.current_stage,
                "applied_at": application.applied_at.isoformat() if application.applied_at else None,
                "is_shortlisted": application.is_shortlisted,
                "ai_score": application.ai_overall_score,
                "ai_recommendation": application.ai_recommendation,
            },
            "job": {
                "id": job.id if job else None,
                "title": job.title if job else None,
            } if job else None,
        }


async def list_candidates(
    job_id: int,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
    is_shortlisted: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List candidates for a job with filtering."""
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.job_id == job_id)
        )
        
        if stage:
            query = query.where(Application.current_stage == stage)
        if status:
            query = query.where(Application.status == status)
        if is_shortlisted is not None:
            query = query.where(Application.is_shortlisted == is_shortlisted)
            
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.join(Candidate).where(
                or_(
                    Candidate.first_name.ilike(search_pattern),
                    Candidate.last_name.ilike(search_pattern),
                    Candidate.email.ilike(search_pattern),
                )
            )
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Application.applied_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        candidates = []
        for app in applications:
            if app.candidate:
                candidates.append({
                    "application_id": app.id,
                    "candidate_id": app.candidate.id,
                    "first_name": app.candidate.first_name,
                    "last_name": app.candidate.last_name,
                    "email": app.candidate.email,
                    "current_title": app.candidate.current_title,
                    "experience_years": app.candidate.experience_years,
                    "stage": app.current_stage,
                    "status": app.status,
                    "is_shortlisted": app.is_shortlisted,
                    "ai_score": app.ai_overall_score,
                    "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                })
        
        return {
            "candidates": candidates,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def shortlist_candidate(
    application_id: int,
    reason: Optional[str] = None,
    shortlisted_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Shortlist a candidate."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application).where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
            
        if application.status == "rejected":
            return {"success": False, "error": "Cannot shortlist a rejected application"}
        
        application.is_shortlisted = True
        application.current_stage = "shortlisted"
        
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.SHORTLISTED,
            performed_by_id=shortlisted_by,
            details={"reason": reason} if reason else None,
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "application_id": application_id,
            "stage": application.current_stage,
            "is_shortlisted": True,
        }


async def reject_candidate(
    application_id: int,
    reason: str,
    send_notification: bool = True,
    rejected_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Reject a candidate's application."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
            
        if application.status == "rejected":
            return {"success": False, "error": "Application is already rejected"}
        
        application.status = "rejected"
        application.current_stage = "rejected"
        application.rejection_reason = reason
        
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.REJECTED,
            performed_by_id=rejected_by,
            details={"reason": reason, "send_notification": send_notification},
        )
        session.add(activity)
        
        await session.commit()
        
        email_queued = False
        if send_notification and application.candidate:
            from workers.tasks import queue_rejection_email
            try:
                await queue_rejection_email(application_id)
                email_queued = True
            except Exception as e:
                logger.warning(f"Failed to queue rejection email: {e}")
        
        return {
            "success": True,
            "application_id": application_id,
            "status": "rejected",
            "email_queued": email_queued,
        }


async def get_candidate_documents(application_id: int) -> Dict[str, Any]:
    """Get all documents for an application."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.files))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"error": "Application not found"}
        
        documents = {
            "resume": None,
            "cover_letters": [],
            "portfolios": [],
            "other": [],
        }
        
        for file in application.files:
            doc_info = {
                "id": file.id,
                "filename": file.original_filename,
                "file_type": file.file_type,
                "size_bytes": file.size_bytes,
                "uploaded_at": file.created_at.isoformat() if file.created_at else None,
            }
            
            if file.file_type == "resume":
                documents["resume"] = doc_info
            elif file.file_type == "cover_letter":
                documents["cover_letters"].append(doc_info)
            elif file.file_type == "portfolio":
                documents["portfolios"].append(doc_info)
            else:
                documents["other"].append(doc_info)
        
        return {
            "application_id": application_id,
            "documents": documents,
        }
