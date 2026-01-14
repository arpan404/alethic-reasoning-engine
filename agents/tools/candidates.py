"""Candidate management tools for Alethic agents.

These tools provide database operations for managing candidates,
including retrieval, status updates, and actions like shortlisting/rejection.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.candidates import Candidate, CandidateStatus
from database.models.applications import Application
from database.models.files import File

logger = logging.getLogger(__name__)


async def get_candidate(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a candidate.
    
    Args:
        candidate_id: The unique identifier of the candidate
        
    Returns:
        Dictionary containing candidate details, or None if not found
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Candidate)
            .options(
                selectinload(Candidate.education),
                selectinload(Candidate.experience),
                selectinload(Candidate.applications),
            )
            .where(Candidate.id == candidate_id)
        )
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return None
        
        return {
            "id": candidate.id,
            "name": f"{candidate.first_name} {candidate.last_name}".strip(),
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "status": candidate.status,
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
            "application_count": len(candidate.applications or []),
        }


async def list_candidates(
    job_id: Optional[int] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
    skills: Optional[List[str]] = None,
    min_experience: Optional[int] = None,
    max_experience: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List candidates with optional filtering.
    
    Args:
        job_id: Filter by candidates who applied to this job
        status: Filter by candidate status (active, inactive, etc.)
        search_query: Search by name or email
        skills: Filter by required skills
        min_experience: Minimum years of experience
        max_experience: Maximum years of experience
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        Dictionary with candidates list and pagination info
    """
    async with AsyncSessionLocal() as session:
        query = select(Candidate)
        conditions = []
        
        # Filter by job (via applications)
        if job_id:
            query = query.join(Application).where(Application.job_id == job_id)
        
        # Filter by status
        if status:
            conditions.append(Candidate.status == status)
        
        # Search by name or email
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(
                or_(
                    Candidate.first_name.ilike(search_pattern),
                    Candidate.last_name.ilike(search_pattern),
                    Candidate.email.ilike(search_pattern),
                )
            )
        
        # Filter by experience
        if min_experience is not None:
            conditions.append(Candidate.years_of_experience >= min_experience)
        if max_experience is not None:
            conditions.append(Candidate.years_of_experience <= max_experience)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await session.execute(query)
        candidates = result.scalars().all()
        
        return {
            "candidates": [
                {
                    "id": c.id,
                    "name": f"{c.first_name} {c.last_name}".strip(),
                    "email": c.email,
                    "status": c.status,
                    "headline": c.headline,
                    "experience_level": c.experience_level,
                    "years_of_experience": c.years_of_experience,
                    "skills": (c.skills or [])[:10],  # First 10 skills
                    "location": c.location,
                }
                for c in candidates
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(candidates)) < total_count,
        }


async def update_candidate_status(
    candidate_id: int,
    status: str,
    reason: Optional[str] = None,
    updated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Update a candidate's status.
    
    Args:
        candidate_id: The candidate to update
        status: New status (active, inactive, blacklisted, verified, pending_verification)
        reason: Optional reason for the status change
        updated_by: User ID who is making the update
        
    Returns:
        Dictionary with success status and updated candidate info
    """
    valid_statuses = [s.value for s in CandidateStatus]
    if status not in valid_statuses:
        return {
            "success": False,
            "error": f"Invalid status '{status}'. Valid options: {valid_statuses}",
        }
    
    async with AsyncSessionLocal() as session:
        query = select(Candidate).where(Candidate.id == candidate_id)
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return {
                "success": False,
                "error": f"Candidate with ID {candidate_id} not found",
            }
        
        old_status = candidate.status
        candidate.status = status
        candidate.updated_at = datetime.utcnow()
        if updated_by:
            candidate.updated_by = updated_by
        
        await session.commit()
        
        logger.info(
            f"Updated candidate {candidate_id} status: {old_status} -> {status}"
            + (f" (reason: {reason})" if reason else "")
        )
        
        return {
            "success": True,
            "candidate_id": candidate_id,
            "old_status": old_status,
            "new_status": status,
            "reason": reason,
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
            from agents.tools.queue import enqueue_task
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


async def get_candidate_documents(candidate_id: int) -> Dict[str, Any]:
    """Get all documents associated with a candidate.
    
    Args:
        candidate_id: The candidate ID
        
    Returns:
        Dictionary containing resume, cover letter, portfolio items, etc.
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Candidate)
            .options(
                selectinload(Candidate.resume_file),
                selectinload(Candidate.applications).selectinload(Application.files),
            )
            .where(Candidate.id == candidate_id)
        )
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return {
                "success": False,
                "error": f"Candidate with ID {candidate_id} not found",
            }
        
        documents = {
            "candidate_id": candidate_id,
            "name": f"{candidate.first_name} {candidate.last_name}".strip(),
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
        
        # Get documents from applications
        for app in (candidate.applications or []):
            for file in (app.files or []):
                doc_info = {
                    "id": file.id,
                    "filename": file.original_filename,
                    "file_type": file.file_type,
                    "application_id": app.id,
                    "job_id": app.job_id,
                }
                
                if file.file_type == "cover_letter":
                    documents["cover_letters"].append(doc_info)
                elif file.file_type == "portfolio":
                    documents["portfolios"].append(doc_info)
                else:
                    documents["other_documents"].append(doc_info)
        
        return documents
