"""Bulk operations tools for Alethic agents.

These tools handle bulk operations like uploading multiple resumes,
bulk rejection, and bulk stage transitions.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application
from database.models.files import File
from agents.tools.queue import enqueue_task, get_task_status

logger = logging.getLogger(__name__)


async def upload_resumes_bulk(
    job_id: int,
    file_ids: List[int],
    auto_evaluate: bool = True,
    uploaded_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Upload multiple resumes for a job and queue processing.
    
    This is used for HR-driven bulk hiring where multiple
    resumes need to be processed and evaluated.
    
    Args:
        job_id: The job to associate resumes with
        file_ids: List of uploaded file IDs to process
        auto_evaluate: Whether to automatically trigger evaluation
        uploaded_by: User ID who is uploading
        
    Returns:
        Dictionary with upload job details and task ID
    """
    if not file_ids:
        return {
            "success": False,
            "error": "No files provided",
        }
    
    # Verify files exist
    async with AsyncSessionLocal() as session:
        file_query = select(File).where(File.id.in_(file_ids))
        result = await session.execute(file_query)
        files = result.scalars().all()
        
        if len(files) != len(file_ids):
            found_ids = {f.id for f in files}
            missing_ids = [fid for fid in file_ids if fid not in found_ids]
            return {
                "success": False,
                "error": f"Some files not found: {missing_ids}",
            }
    
    # Queue the bulk processing job
    task_result = await enqueue_task(
        task_type="bulk_resume_processing",
        payload={
            "job_id": job_id,
            "file_ids": file_ids,
            "auto_evaluate": auto_evaluate,
            "uploaded_by": uploaded_by,
        },
        priority="normal",
    )
    
    logger.info(
        f"Queued bulk resume upload for job {job_id}: {len(file_ids)} files"
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "file_count": len(file_ids),
        "task_id": task_result.get("task_id"),
        "auto_evaluate": auto_evaluate,
        "message": f"Bulk upload queued. Processing {len(file_ids)} resumes.",
    }


async def get_bulk_upload_status(upload_task_id: str) -> Dict[str, Any]:
    """Get the status of a bulk upload job.
    
    Args:
        upload_task_id: The task ID from upload_resumes_bulk
        
    Returns:
        Dictionary with processing status and progress
    """
    
    status = await get_task_status(upload_task_id)
    
    if not status.get("found"):
        return {
            "found": False,
            "error": f"Task {upload_task_id} not found",
        }
    
    return {
        "found": True,
        "task_id": upload_task_id,
        "status": status.get("status"),
        "progress": status.get("progress", {}),
        "results": status.get("results", {}),
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "errors": status.get("errors", []),
    }


async def bulk_reject_candidates(
    application_ids: List[int],
    reason: str,
    send_emails: bool = True,
    rejected_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Reject multiple candidates at once.
    
    Args:
        application_ids: List of application IDs to reject
        reason: Reason for rejection
        send_emails: Whether to send rejection emails
        rejected_by: User ID who is rejecting
        
    Returns:
        Dictionary with rejection results
    """
    if not application_ids:
        return {
            "success": False,
            "error": "No applications provided",
        }
    
    async with AsyncSessionLocal() as session:
        # Get applications
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id.in_(application_ids))
        )
        result = await session.execute(query)
        applications = result.scalars().all()
        
        if not applications:
            return {
                "success": False,
                "error": "No applications found with provided IDs",
            }
        
        # Track results
        rejected = []
        skipped = []
        
        for app in applications:
            # Skip already rejected
            if app.status == "rejected":
                skipped.append({
                    "application_id": app.id,
                    "reason": "Already rejected",
                })
                continue
            
            # Reject the application
            app.current_stage = "rejected"
            app.status = "rejected"
            app.rejection_reason = reason
            app.rejected_at = datetime.utcnow()
            app.updated_at = datetime.utcnow()
            if rejected_by:
                app.updated_by = rejected_by
            
            candidate_name = ""
            if app.candidate:
                candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
            
            rejected.append({
                "application_id": app.id,
                "candidate_name": candidate_name,
            })
        
        await session.commit()
    
    # Queue rejection emails if requested
    if send_emails and rejected:
        await enqueue_task(
            task_type="bulk_send_emails",
            payload={
                "email_type": "rejection",
                "application_ids": [r["application_id"] for r in rejected],
                "sent_by": rejected_by,
            },
            priority="low",
        )
    
    logger.info(
        f"Bulk rejected {len(rejected)} applications "
        f"(skipped {len(skipped)}, emails: {send_emails})"
    )
    
    return {
        "success": True,
        "rejected_count": len(rejected),
        "skipped_count": len(skipped),
        "rejected": rejected,
        "skipped": skipped,
        "emails_queued": send_emails and len(rejected) > 0,
        "reason": reason,
    }


async def bulk_move_stage(
    application_ids: List[int],
    new_stage: str,
    reason: Optional[str] = None,
    moved_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Move multiple applications to a new stage.
    
    Args:
        application_ids: List of application IDs to move
        new_stage: The new stage name
        reason: Optional reason for the move
        moved_by: User ID who is moving
        
    Returns:
        Dictionary with move results
    """
    if not application_ids:
        return {
            "success": False,
            "error": "No applications provided",
        }
    
    async with AsyncSessionLocal() as session:
        # Get applications
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id.in_(application_ids))
        )
        result = await session.execute(query)
        applications = result.scalars().all()
        
        if not applications:
            return {
                "success": False,
                "error": "No applications found with provided IDs",
            }
        
        # Track results
        moved = []
        skipped = []
        
        for app in applications:
            # Skip if already in target stage
            if app.current_stage == new_stage:
                skipped.append({
                    "application_id": app.id,
                    "reason": f"Already in stage '{new_stage}'",
                })
                continue
            
            old_stage = app.current_stage
            app.current_stage = new_stage
            app.updated_at = datetime.utcnow()
            if moved_by:
                app.updated_by = moved_by
            
            candidate_name = ""
            if app.candidate:
                candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
            
            moved.append({
                "application_id": app.id,
                "candidate_name": candidate_name,
                "old_stage": old_stage,
                "new_stage": new_stage,
            })
        
        await session.commit()
    
    logger.info(
        f"Bulk moved {len(moved)} applications to '{new_stage}' "
        f"(skipped {len(skipped)})"
    )
    
    return {
        "success": True,
        "moved_count": len(moved),
        "skipped_count": len(skipped),
        "moved": moved,
        "skipped": skipped,
        "new_stage": new_stage,
        "reason": reason,
    }
