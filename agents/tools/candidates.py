"""Candidate management tools for Alethic agents.

These tools provide database operations for managing candidates,
including retrieval, status updates, and actions like shortlisting/rejection.

IMPORTANT: All tools are scoped through Application for multi-tenant isolation.
Candidates can apply across organizations, so we always access via Application → Job → Org.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.candidates import Candidate, CandidateStatus
from database.models.applications import Application
from database.models.jobs import Job
from database.models.files import File
from agents.tools.queue import enqueue_task
from core.cache import cache

def _get_candidate_cache_key(func, application_id, *args, **kwargs):
    return f"candidate:app:{application_id}"

logger = logging.getLogger(__name__)


@cache(ttl=300, key_builder=_get_candidate_cache_key)
async def get_candidate_for_application(application_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a candidate via their application.
    
    This ensures proper multi-tenant isolation by accessing the candidate
    through the Application model, which is tied to a specific Job/Organization.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary containing candidate details, or None if not found
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(
                selectinload(Application.candidate).selectinload(Candidate.education),
                selectinload(Application.candidate).selectinload(Candidate.experience),
                selectinload(Application.job),
            )
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return None
        
        candidate = app.candidate
        if not candidate:
            return None
        
        return {
            "application_id": application_id,
            "job_id": app.job_id,
            "job_title": app.job.title if app.job else None,
            "candidate_id": candidate.id,
            "name": f"{candidate.first_name} {candidate.last_name}".strip(),
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "headline": candidate.headline,
            "summary": candidate.summary,
            "linkedin_url": candidate.linkedin_url,
            "github_url": candidate.github_url,
            "portfolio_url": candidate.portfolio_url,
            "experience_level": candidate.experience_level,
            "years_of_experience": candidate.years_of_experience,
            "education_level": candidate.education_level,
            "skills": candidate.skills or [],
            "languages": candidate.languages or [],
            "work_authorization": candidate.work_authorization,
            "salary_expectation_min": candidate.salary_expectation_min,
            "salary_expectation_max": candidate.salary_expectation_max,
            "salary_currency": candidate.salary_currency,
            "source": candidate.source,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "education": [
                {
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study,
                    "start_date": edu.start_date.isoformat() if edu.start_date else None,
                    "end_date": edu.end_date.isoformat() if edu.end_date else None,
                    "gpa": edu.gpa,
                }
                for edu in (candidate.education or [])
            ],
            "experience": [
                {
                    "company": exp.company,
                    "title": exp.title,
                    "location": exp.location,
                    "description": exp.description,
                    "start_date": exp.start_date.isoformat() if exp.start_date else None,
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "is_current": exp.is_current,
                }
                for exp in (candidate.experience or [])
            ],
            # Application-specific data
            "application_status": app.status,
            "current_stage": app.current_stage,
            "ai_recommendation": app.ai_recommendation,
            "ai_overall_score": app.ai_overall_score,
        }


async def list_candidates_for_job(
    job_id: int,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
    min_experience: Optional[int] = None,
    max_experience: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List candidates who applied to a specific job.
    
    Multi-tenant safe: job_id ensures we only see candidates
    for jobs within the caller's organization.
    
    Args:
        job_id: The job to list candidates for (required for org scoping)
        stage: Filter by application stage
        status: Filter by application status
        search_query: Search by name or email
        min_experience: Minimum years of experience
        max_experience: Maximum years of experience
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        Dictionary with candidates list and pagination info
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.job_id == job_id)
        )
        conditions = []
        
        if stage:
            conditions.append(Application.current_stage == stage)
        
        if status:
            conditions.append(Application.status == status)
        
        if search_query:
            # Need subquery for candidate search
            search_pattern = f"%{search_query}%"
            subq = (
                select(Candidate.id)
                .where(
                    or_(
                        Candidate.first_name.ilike(search_pattern),
                        Candidate.last_name.ilike(search_pattern),
                        Candidate.email.ilike(search_pattern),
                    )
                )
            )
            conditions.append(Application.candidate_id.in_(subq))
        
        if min_experience is not None:
            subq = select(Candidate.id).where(Candidate.years_of_experience >= min_experience)
            conditions.append(Application.candidate_id.in_(subq))
        
        if max_experience is not None:
            subq = select(Candidate.id).where(Candidate.years_of_experience <= max_experience)
            conditions.append(Application.candidate_id.in_(subq))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination
        query = query.order_by(Application.created_at.desc()).offset(offset).limit(limit)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        return {
            "job_id": job_id,
            "candidates": [
                {
                    "application_id": a.id,
                    "candidate_id": a.candidate_id,
                    "name": f"{a.candidate.first_name} {a.candidate.last_name}".strip() if a.candidate else None,
                    "email": a.candidate.email if a.candidate else None,
                    "headline": a.candidate.headline if a.candidate else None,
                    "experience_level": a.candidate.experience_level if a.candidate else None,
                    "years_of_experience": a.candidate.years_of_experience if a.candidate else None,
                    "skills": (a.candidate.skills or [])[:10] if a.candidate else [],
                    "location": a.candidate.location if a.candidate else None,
                    # Application data
                    "current_stage": a.current_stage,
                    "status": a.status,
                    "ai_recommendation": a.ai_recommendation,
                    "ai_overall_score": a.ai_overall_score,
                    "is_shortlisted": a.is_shortlisted,
                    "applied_at": a.applied_at.isoformat() if a.applied_at else None,
                }
                for a in applications
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(applications)) < total_count,
        }


async def shortlist_candidate(
    application_id: int,
    reason: str,
    shortlisted_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Shortlist a candidate for a job (moves to shortlisted stage).
    
    Args:
        application_id: The application to shortlist
        reason: Reason for shortlisting (will be recorded as a note)
        shortlisted_by: User ID who is shortlisting
        
    Returns:
        Dictionary with success status and application info
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        old_stage = application.current_stage
        application.current_stage = "shortlisted"
        application.is_shortlisted = True
        application.shortlisted_at = datetime.utcnow()
        application.updated_at = datetime.utcnow()
        if shortlisted_by:
            application.updated_by = shortlisted_by
        
        await session.commit()
        
        candidate_name = ""
        if application.candidate:
            candidate_name = f"{application.candidate.first_name} {application.candidate.last_name}".strip()
        
        logger.info(
            f"Shortlisted application {application_id} "
            f"(candidate: {candidate_name}, reason: {reason})"
        )
        
        return {
            "success": True,
            "application_id": application_id,
            "candidate_name": candidate_name,
            "old_stage": old_stage,
            "new_stage": "shortlisted",
            "reason": reason,
        }


async def reject_candidate(
    application_id: int,
    reason: str,
    send_email: bool = True,
    rejected_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Reject a candidate's application.
    
    Args:
        application_id: The application to reject
        reason: Reason for rejection (will be recorded)
        send_email: Whether to send a rejection email to the candidate
        rejected_by: User ID who is rejecting
        
    Returns:
        Dictionary with success status and next steps
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        old_stage = application.current_stage
        application.current_stage = "rejected"
        application.status = "rejected"
        application.rejection_reason = reason
        application.rejected_at = datetime.utcnow()
        application.updated_at = datetime.utcnow()
        if rejected_by:
            application.updated_by = rejected_by
        
        await session.commit()
        
        candidate_name = ""
        candidate_email = ""
        if application.candidate:
            candidate_name = f"{application.candidate.first_name} {application.candidate.last_name}".strip()
            candidate_email = application.candidate.email
        
        logger.info(
            f"Rejected application {application_id} "
            f"(candidate: {candidate_name}, reason: {reason})"
        )
        
        # Queue rejection email if requested
        email_queued = False
        if send_email and candidate_email:
            await enqueue_task(
                task_type="send_rejection_email",
                payload={
                    "application_id": application_id,
                    "candidate_email": candidate_email,
                    "candidate_name": candidate_name,
                }
            )
            email_queued = True
        
        return {
            "success": True,
            "application_id": application_id,
            "candidate_name": candidate_name,
            "old_stage": old_stage,
            "new_stage": "rejected",
            "reason": reason,
            "email_queued": email_queued,
        }


async def get_application_documents(application_id: int) -> Dict[str, Any]:
    """Get all documents associated with an application.
    
    This properly scopes documents to a specific application,
    ensuring multi-tenant data isolation.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary containing resume, cover letter, portfolio items, etc.
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(
                selectinload(Application.candidate).selectinload(Candidate.resume_file),
                selectinload(Application.files),
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
        
        candidate = app.candidate
        if not candidate:
            return {
                "success": False,
                "error": "Candidate not found for this application",
            }
        
        documents = {
            "application_id": application_id,
            "candidate_id": candidate.id,
            "candidate_name": f"{candidate.first_name} {candidate.last_name}".strip(),
            "job_id": app.job_id,
            "resume": None,
            "cover_letters": [],
            "portfolios": [],
            "other_documents": [],
        }
        
        # Get resume from candidate profile
        if candidate.resume_file:
            documents["resume"] = {
                "id": candidate.resume_file.id,
                "filename": candidate.resume_file.original_filename,
                "uploaded_at": candidate.resume_file.created_at.isoformat() if candidate.resume_file.created_at else None,
            }
        
        # Get documents from this application only
        for file in (app.files or []):
            doc_info = {
                "id": file.id,
                "filename": file.original_filename,
                "file_type": file.file_type,
            }
            
            if file.file_type == "cover_letter":
                documents["cover_letters"].append(doc_info)
            elif file.file_type == "portfolio":
                documents["portfolios"].append(doc_info)
            elif file.file_type == "resume":
                # Application-specific resume overrides candidate resume
                documents["resume"] = doc_info
            else:
                documents["other_documents"].append(doc_info)
        
        return documents
