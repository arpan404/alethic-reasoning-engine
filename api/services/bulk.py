"""
Bulk operations service functions for API endpoints.

Provides direct database operations for bulk actions,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application, ApplicationActivity, ApplicationActivityType

logger = logging.getLogger(__name__)


async def upload_resumes_bulk(
    job_id: int,
    file_paths: List[str],
    source: str = "bulk_upload",
) -> Dict[str, Any]:
    """
    Queue bulk resume upload for processing.
    
    Args:
        job_id: Job ID to create applications for
        file_paths: List of file paths/URLs to process
        source: Source label for the uploads
        
    Returns:
        Dictionary with task ID for tracking
    """
    task_id = f"bulk_upload_{uuid.uuid4().hex[:12]}"
    
    try:
        from workers.tasks import queue_bulk_resume_upload
        await queue_bulk_resume_upload(
            task_id=task_id,
            job_id=job_id,
            file_paths=file_paths,
            source=source,
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "job_id": job_id,
            "files_queued": len(file_paths),
            "status": "queued",
        }
    except Exception as e:
        logger.error(f"Failed to queue bulk upload: {e}")
        return {"success": False, "error": str(e)}


async def get_bulk_upload_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a bulk upload task.
    
    Args:
        task_id: The task ID to check
        
    Returns:
        Dictionary with task status and progress
    """
    try:
        from core.cache import redis_cache
        
        # Get task status from Redis
        status = await redis_cache.get(f"bulk_upload:{task_id}")
        
        if not status:
            return {
                "task_id": task_id,
                "status": "not_found",
                "error": "Task not found or expired",
            }
        
        return {
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "total": status.get("total", 0),
            "processed": status.get("processed", 0),
            "successful": status.get("successful", 0),
            "failed": status.get("failed", 0),
            "errors": status.get("errors", []),
        }
    except Exception as e:
        logger.error(f"Failed to get bulk upload status: {e}")
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e),
        }


async def bulk_reject_candidates(
    application_ids: List[int],
    reason: str,
    send_notification: bool = True,
    rejected_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Reject multiple candidates at once.
    
    Args:
        application_ids: List of application IDs to reject
        reason: Rejection reason
        send_notification: Whether to send rejection emails
        rejected_by: User ID who initiated rejection
        
    Returns:
        Dictionary with results
    """
    task_id = f"bulk_reject_{uuid.uuid4().hex[:12]}"
    
    async with AsyncSessionLocal() as session:
        results = {
            "successful": [],
            "failed": [],
        }
        
        for app_id in application_ids:
            try:
                result = await session.execute(
                    select(Application).where(Application.id == app_id)
                )
                application = result.scalar_one_or_none()
                
                if not application:
                    results["failed"].append({
                        "application_id": app_id,
                        "error": "Not found",
                    })
                    continue
                
                if application.status == "rejected":
                    results["failed"].append({
                        "application_id": app_id,
                        "error": "Already rejected",
                    })
                    continue
                
                application.status = "rejected"
                application.current_stage = "rejected"
                application.rejection_reason = reason
                
                # Record activity
                activity = ApplicationActivity(
                    application_id=app_id,
                    activity_type=ApplicationActivityType.REJECTED,
                    performed_by_id=rejected_by,
                    details={"reason": reason, "bulk": True},
                )
                session.add(activity)
                
                results["successful"].append(app_id)
                
            except Exception as e:
                results["failed"].append({
                    "application_id": app_id,
                    "error": str(e),
                })
        
        await session.commit()
    
    # Queue notification emails
    if send_notification and results["successful"]:
        try:
            from workers.tasks import queue_bulk_rejection_emails
            await queue_bulk_rejection_emails(results["successful"], reason)
        except Exception as e:
            logger.warning(f"Failed to queue rejection emails: {e}")
    
    return {
        "task_id": task_id,
        "total": len(application_ids),
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "successful_ids": results["successful"],
        "failures": results["failed"],
    }


async def bulk_move_stage(
    application_ids: List[int],
    new_stage: str,
    reason: Optional[str] = None,
    moved_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Move multiple applications to a new stage.
    
    Args:
        application_ids: List of application IDs to move
        new_stage: Target stage
        reason: Reason for stage change
        moved_by: User ID who initiated the move
        
    Returns:
        Dictionary with results
    """
    task_id = f"bulk_move_{uuid.uuid4().hex[:12]}"
    
    async with AsyncSessionLocal() as session:
        results = {
            "successful": [],
            "failed": [],
        }
        
        for app_id in application_ids:
            try:
                result = await session.execute(
                    select(Application).where(Application.id == app_id)
                )
                application = result.scalar_one_or_none()
                
                if not application:
                    results["failed"].append({
                        "application_id": app_id,
                        "error": "Not found",
                    })
                    continue
                
                old_stage = application.current_stage
                application.current_stage = new_stage
                
                # Record activity
                activity = ApplicationActivity(
                    application_id=app_id,
                    activity_type=ApplicationActivityType.STAGE_CHANGED,
                    performed_by_id=moved_by,
                    details={
                        "old_stage": old_stage,
                        "new_stage": new_stage,
                        "reason": reason,
                        "bulk": True,
                    },
                )
                session.add(activity)
                
                results["successful"].append({
                    "application_id": app_id,
                    "old_stage": old_stage,
                    "new_stage": new_stage,
                })
                
            except Exception as e:
                results["failed"].append({
                    "application_id": app_id,
                    "error": str(e),
                })
        
        await session.commit()
    
    return {
        "task_id": task_id,
        "total": len(application_ids),
        "successful": len(results["successful"]),
        "failed": len(results["failed"]),
        "results": results["successful"],
        "failures": results["failed"],
    }
