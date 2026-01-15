"""
Application service functions for API endpoints.

Provides direct database operations for application management,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, func
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

logger = logging.getLogger(__name__)


async def get_application(application_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary containing application details, or None if not found
    """
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
        
        if not application:
            return None
            
        candidate = application.candidate
        job = application.job
        
        return {
            "id": application.id,
            "status": application.status,
            "current_stage": application.current_stage,
            "applied_at": application.applied_at.isoformat() if application.applied_at else None,
            "updated_at": application.updated_at.isoformat() if application.updated_at else None,
            "is_shortlisted": application.is_shortlisted,
            "source": application.source,
            "ai_overall_score": application.ai_overall_score,
            "ai_recommendation": application.ai_recommendation,
            "rejection_reason": application.rejection_reason,
            "candidate": {
                "id": candidate.id,
                "first_name": candidate.first_name,
                "last_name": candidate.last_name,
                "email": candidate.email,
            } if candidate else None,
            "job": {
                "id": job.id,
                "title": job.title,
                "department": job.department,
            } if job else None,
        }


async def list_applications(
    job_id: int,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    is_shortlisted: Optional[bool] = None,
    sort_by: str = "applied_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List applications for a job with filtering.
    
    Args:
        job_id: The job ID to list applications for
        stage: Filter by current stage
        status: Filter by status
        is_shortlisted: Filter by shortlisted status
        sort_by: Field to sort by
        sort_order: Sort order (asc/desc)
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        Dictionary with applications list and pagination info
    """
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
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply sorting
        sort_column = getattr(Application, sort_by, Application.applied_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        app_list = []
        for app in applications:
            app_list.append({
                "id": app.id,
                "candidate_id": app.candidate_id,
                "candidate_name": f"{app.candidate.first_name} {app.candidate.last_name}" if app.candidate else None,
                "status": app.status,
                "current_stage": app.current_stage,
                "is_shortlisted": app.is_shortlisted,
                "ai_score": app.ai_overall_score,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            })
        
        return {
            "applications": app_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def move_application_stage(
    application_id: int,
    new_stage: str,
    reason: Optional[str] = None,
    moved_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Move an application to a new stage in the pipeline.
    
    Args:
        application_id: The application to move
        new_stage: The new stage name
        reason: Optional reason for the stage change
        moved_by: User ID who initiated the move
        
    Returns:
        Dictionary with success status and stage info
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application).where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
        
        old_stage = application.current_stage
        application.current_stage = new_stage
        application.updated_at = datetime.utcnow()
        
        # Record activity
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.STAGE_CHANGED,
            performed_by_id=moved_by,
            details={
                "old_stage": old_stage,
                "new_stage": new_stage,
                "reason": reason,
            },
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "application_id": application_id,
            "old_stage": old_stage,
            "new_stage": new_stage,
        }


async def get_application_history(application_id: int) -> Dict[str, Any]:
    """
    Get the full activity history for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with chronological activity history
    """
    async with AsyncSessionLocal() as session:
        # Get activities
        result = await session.execute(
            select(ApplicationActivity)
            .where(ApplicationActivity.application_id == application_id)
            .order_by(ApplicationActivity.created_at.desc())
        )
        activities = result.scalars().all()
        
        # Get notes
        notes_result = await session.execute(
            select(ApplicationNote)
            .where(ApplicationNote.application_id == application_id)
            .order_by(ApplicationNote.created_at.desc())
        )
        notes = notes_result.scalars().all()
        
        history = []
        
        for activity in activities:
            history.append({
                "type": "activity",
                "activity_type": activity.activity_type.value if hasattr(activity.activity_type, 'value') else str(activity.activity_type),
                "details": activity.details,
                "performed_by": activity.performed_by_id,
                "timestamp": activity.created_at.isoformat() if activity.created_at else None,
            })
        
        for note in notes:
            history.append({
                "type": "note",
                "content": note.content,
                "is_private": note.is_private,
                "created_by": note.created_by_id,
                "timestamp": note.created_at.isoformat() if note.created_at else None,
            })
        
        # Sort by timestamp
        history.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        
        return {
            "application_id": application_id,
            "history": history,
            "total_activities": len(activities),
            "total_notes": len(notes),
        }
