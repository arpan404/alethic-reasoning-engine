"""Task queue tools for Alethic agents.

These tools manage async task operations like evaluation triggers,
email sending, and bulk processing.
"""

from typing import Any, Dict, Optional
from datetime import datetime
import uuid
import logging

from sqlalchemy import select

from database.engine import AsyncSessionLocal

logger = logging.getLogger(__name__)


# In-memory task store for development
# In production, this would use Redis/Celery/etc.
_task_store: Dict[str, Dict[str, Any]] = {}


async def enqueue_task(
    task_type: str,
    payload: Dict[str, Any],
    priority: str = "normal",
    scheduled_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Enqueue a background task for processing.
    
    Args:
        task_type: Type of task (pre_evaluation, full_evaluation, send_email, etc.)
        payload: Task payload data
        priority: Priority level (low, normal, high, urgent)
        scheduled_at: Optional scheduled execution time
        
    Returns:
        Dictionary with task_id and queue status
    """
    valid_priorities = ["low", "normal", "high", "urgent"]
    if priority not in valid_priorities:
        return {
            "success": False,
            "error": f"Invalid priority '{priority}'. Valid options: {valid_priorities}",
        }
    
    task_id = str(uuid.uuid4())
    
    task_data = {
        "id": task_id,
        "type": task_type,
        "payload": payload,
        "priority": priority,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "started_at": None,
        "completed_at": None,
        "progress": {},
        "results": {},
        "errors": [],
    }
    
    _task_store[task_id] = task_data
    
    logger.info(f"Enqueued task {task_id} ({task_type}) with priority {priority}")
    
    # In production, this would actually enqueue to Celery/Redis/etc.
    # For now, we just store it and the worker would pick it up
    
    return {
        "success": True,
        "task_id": task_id,
        "task_type": task_type,
        "priority": priority,
        "status": "queued",
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
    }


async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the current status of a queued task.
    
    Args:
        task_id: The task ID
        
    Returns:
        Dictionary with task status and progress
    """
    task = _task_store.get(task_id)
    
    if not task:
        return {
            "found": False,
            "error": f"Task {task_id} not found",
        }
    
    return {
        "found": True,
        "task_id": task_id,
        "type": task["type"],
        "status": task["status"],
        "priority": task["priority"],
        "progress": task.get("progress", {}),
        "results": task.get("results", {}),
        "created_at": task["created_at"],
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "errors": task.get("errors", []),
    }


async def cancel_task(task_id: str) -> Dict[str, Any]:
    """Cancel a queued or running task.
    
    Args:
        task_id: The task ID to cancel
        
    Returns:
        Dictionary with cancellation status
    """
    task = _task_store.get(task_id)
    
    if not task:
        return {
            "success": False,
            "error": f"Task {task_id} not found",
        }
    
    if task["status"] == "completed":
        return {
            "success": False,
            "error": "Cannot cancel completed task",
        }
    
    if task["status"] == "cancelled":
        return {
            "success": False,
            "error": "Task already cancelled",
        }
    
    old_status = task["status"]
    task["status"] = "cancelled"
    task["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"Cancelled task {task_id} (was: {old_status})")
    
    return {
        "success": True,
        "task_id": task_id,
        "old_status": old_status,
        "new_status": "cancelled",
    }


# Helper functions for task workers (used internally)

def update_task_status(
    task_id: str,
    status: str,
    progress: Optional[Dict[str, Any]] = None,
    results: Optional[Dict[str, Any]] = None,
    errors: Optional[list] = None,
) -> bool:
    """Update task status (called by workers).
    
    Args:
        task_id: The task ID
        status: New status
        progress: Optional progress update
        results: Optional results update
        errors: Optional errors to add
        
    Returns:
        True if updated, False if task not found
    """
    task = _task_store.get(task_id)
    
    if not task:
        return False
    
    task["status"] = status
    
    if status == "in_progress" and not task.get("started_at"):
        task["started_at"] = datetime.utcnow().isoformat()
    
    if status in ("completed", "failed"):
        task["completed_at"] = datetime.utcnow().isoformat()
    
    if progress:
        task["progress"].update(progress)
    
    if results:
        task["results"].update(results)
    
    if errors:
        task["errors"].extend(errors)
    
    return True
