"""Application management tools for Alethic agents.

These tools provide database operations for managing job applications,
including retrieval, stage transitions, and history tracking.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import (
    Application,
    ApplicationActivity,
    ApplicationActivityType,
    ApplicationNote,
)
from database.models.candidates import Candidate
from database.models.jobs import Job

from core.cache import cache

def _get_application_cache_key(func, application_id, *args, **kwargs):
    return f"application:{application_id}"

def _list_applications_cache_key(func, job_id, stage=None, status=None, *args, **kwargs):
    parts = [f"applications:job:{job_id}"]
    if stage:
        parts.append(f"stage:{stage}")
    if status:
        parts.append(f"status:{status}")
    # We might want to include all filters but for high-level caching this is okay
    # For now, let's cache only based on job, stage, status to avoid explosion
    # Or just cache by job_id if filters are complex and rely on query optimization for filters.
    return ":".join(parts)

logger = logging.getLogger(__name__)


@cache(ttl=60, key_builder=_get_application_cache_key)
async def get_application(application_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about an application.
    
    Args:
        application_id: The unique identifier of the application
        
    Returns:
        Dictionary containing application details, or None if not found
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.job),
                selectinload(Application.notes),
                selectinload(Application.evaluations),
            )
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return None
        
        candidate_info = None
        if app.candidate:
            candidate_info = {
                "id": app.candidate.id,
                "name": f"{app.candidate.first_name} {app.candidate.last_name}".strip(),
                "email": app.candidate.email,
                "phone": app.candidate.phone,
                "headline": app.candidate.headline,
            }
        
        job_info = None
        if app.job:
            job_info = {
                "id": app.job.id,
                "title": app.job.title,
                "department_id": app.job.department_id,
            }
        
        return {
            "id": app.id,
            "candidate": candidate_info,
            "job": job_info,
            "status": app.status,
            "current_stage": app.current_stage,
            "source": app.source,
            "is_shortlisted": app.is_shortlisted,
            "is_starred": app.is_starred,
            # AI Scores
            "ai_screening_status": app.ai_screening_status,
            "ai_recommendation": app.ai_recommendation,
            "ai_match_score": app.ai_match_score,
            "ai_skills_score": app.ai_skills_score,
            "ai_experience_score": app.ai_experience_score,
            "ai_overall_score": app.ai_overall_score,
            "ai_summary": app.ai_summary,
            # Dates
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "shortlisted_at": app.shortlisted_at.isoformat() if app.shortlisted_at else None,
            "rejected_at": app.rejected_at.isoformat() if app.rejected_at else None,
            "rejection_reason": app.rejection_reason,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            # Notes summary
            "notes_count": len(app.notes or []),
            "evaluations_count": len(app.evaluations or []),
        }


async def list_applications(
    job_id: int,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    is_shortlisted: Optional[bool] = None,
    ai_recommendation: Optional[str] = None,
    min_score: Optional[float] = None,
    sort_by: str = "applied_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List applications for a job with filtering and sorting.
    
    Args:
        job_id: The job to list applications for
        stage: Filter by current stage
        status: Filter by status
        is_shortlisted: Filter by shortlisted status
        ai_recommendation: Filter by AI recommendation (strong_match, match, weak_match, no_match)
        min_score: Filter by minimum AI overall score
        sort_by: Field to sort by (applied_at, ai_overall_score, created_at)
        sort_order: Sort order (asc, desc)
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        Dictionary with applications list and pagination info
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
        
        if is_shortlisted is not None:
            conditions.append(Application.is_shortlisted == is_shortlisted)
        
        if ai_recommendation:
            conditions.append(Application.ai_recommendation == ai_recommendation)
        
        if min_score is not None:
            conditions.append(Application.ai_overall_score >= min_score)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar()
        
        # Sort
        sort_column = getattr(Application, sort_by, Application.applied_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        return {
            "applications": [
                {
                    "id": a.id,
                    "candidate_id": a.candidate_id,
                    "candidate_name": f"{a.candidate.first_name} {a.candidate.last_name}".strip() if a.candidate else None,
                    "candidate_email": a.candidate.email if a.candidate else None,
                    "status": a.status,
                    "current_stage": a.current_stage,
                    "is_shortlisted": a.is_shortlisted,
                    "ai_recommendation": a.ai_recommendation,
                    "ai_overall_score": a.ai_overall_score,
                    "ai_match_score": a.ai_match_score,
                    "applied_at": a.applied_at.isoformat() if a.applied_at else None,
                }
                for a in applications
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(applications)) < total_count,
        }


async def move_candidate_stage(
    application_id: int,
    new_stage: str,
    reason: Optional[str] = None,
    moved_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Move an application to a new stage in the pipeline.
    
    Args:
        application_id: The application to move
        new_stage: The new stage name
        reason: Optional reason for the stage change
        moved_by: User ID who is moving the application
        
    Returns:
        Dictionary with success status and stage transition info
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        old_stage = app.current_stage
        app.current_stage = new_stage
        app.updated_at = datetime.utcnow()
        if moved_by:
            app.updated_by = moved_by
        
        # Log the activity
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.STATUS_CHANGED,
            description=f"Stage changed from '{old_stage}' to '{new_stage}'",
            old_value=old_stage,
            new_value=new_stage,
            created_by=moved_by,
        )
        session.add(activity)
        
        await session.commit()
        
        candidate_name = ""
        if app.candidate:
            candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
        
        logger.info(
            f"Moved application {application_id} from '{old_stage}' to '{new_stage}'"
            + (f" (reason: {reason})" if reason else "")
        )
        
        return {
            "success": True,
            "application_id": application_id,
            "candidate_name": candidate_name,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "reason": reason,
        }


async def get_application_history(application_id: int) -> Dict[str, Any]:
    """Get the full activity history for an application.
    
    This includes stage transitions, notes, evaluations, and other activities.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with chronological activity history
    """
    async with AsyncSessionLocal() as session:
        # Get activities
        activity_query = (
            select(ApplicationActivity)
            .where(ApplicationActivity.application_id == application_id)
            .order_by(desc(ApplicationActivity.created_at))
        )
        activity_result = await session.execute(activity_query)
        activities = activity_result.scalars().all()
        
        # Get notes
        notes_query = (
            select(ApplicationNote)
            .where(ApplicationNote.application_id == application_id)
            .order_by(desc(ApplicationNote.created_at))
        )
        notes_result = await session.execute(notes_query)
        notes = notes_result.scalars().all()
        
        # Combine and sort chronologically
        history = []
        
        for activity in activities:
            history.append({
                "type": "activity",
                "activity_type": activity.activity_type,
                "description": activity.description,
                "old_value": activity.old_value,
                "new_value": activity.new_value,
                "created_by": activity.created_by,
                "created_at": activity.created_at.isoformat() if activity.created_at else None,
            })
        
        for note in notes:
            history.append({
                "type": "note",
                "content": note.content,
                "visibility": note.visibility,
                "is_pinned": note.is_pinned,
                "created_by": note.created_by,
                "created_at": note.created_at.isoformat() if note.created_at else None,
            })
        
        # Sort by created_at descending
        history.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "application_id": application_id,
            "history": history,
            "activity_count": len(activities),
            "notes_count": len(notes),
        }
