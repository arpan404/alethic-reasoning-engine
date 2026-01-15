"""Background check service functions."""

from typing import Any, Optional
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.background_checks import BackgroundCheck, BackgroundCheckStatus
from database.models.applications import Application, ApplicationActivity, ApplicationActivityType

logger = logging.getLogger(__name__)


async def initiate_background_check(
    application_id: int,
    check_types: list[str],
    priority: str = "normal",
    initiated_by: Optional[int] = None,
) -> dict[str, Any]:
    """Initiate a background check."""
    async with AsyncSessionLocal() as session:
        app_result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = app_result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
        
        if not application.candidate:
            return {"success": False, "error": "No candidate linked to application"}
        
        check = BackgroundCheck(
            application_id=application_id,
            candidate_id=application.candidate_id,
            check_types=check_types,
            priority=priority,
            status=BackgroundCheckStatus.PENDING,
            initiated_by_id=initiated_by,
        )
        session.add(check)
        await session.flush()
        
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.BACKGROUND_CHECK_INITIATED,
            performed_by_id=initiated_by,
            details={
                "check_id": check.id,
                "check_types": check_types,
                "priority": priority,
            },
        )
        session.add(activity)
        
        await session.commit()
        
        try:
            from workers.tasks import queue_background_check
            await queue_background_check(check.id)
        except Exception as e:
            logger.warning(f"Failed to queue background check: {e}")
        
        return {
            "success": True,
            "check_id": check.id,
            "application_id": application_id,
            "check_types": check_types,
            "priority": priority,
            "status": "pending",
        }


async def get_background_check_status(check_id: int) -> Optional[dict[str, Any]]:
    """Get status of a background check."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BackgroundCheck).where(BackgroundCheck.id == check_id)
        )
        check = result.scalar_one_or_none()
        
        if not check:
            return None
        
        status_value = check.status.value if hasattr(check.status, 'value') else str(check.status)
        
        return {
            "check_id": check.id,
            "application_id": check.application_id,
            "status": status_value,
            "check_types": check.check_types,
            "priority": check.priority,
            "initiated_at": check.created_at.isoformat() if check.created_at else None,
            "updated_at": check.updated_at.isoformat() if check.updated_at else None,
            "estimated_completion": check.estimated_completion.isoformat() if hasattr(check, 'estimated_completion') and check.estimated_completion else None,
        }


async def get_background_check_results(check_id: int) -> Optional[dict[str, Any]]:
    """Get results of a completed background check."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BackgroundCheck).where(BackgroundCheck.id == check_id)
        )
        check = result.scalar_one_or_none()
        
        if not check:
            return None
        
        status_value = check.status.value if hasattr(check.status, 'value') else str(check.status)
        
        if status_value not in ["completed", "completed_with_issues"]:
            return {
                "check_id": check.id,
                "status": status_value,
                "message": "Background check not yet completed",
            }
        
        return {
            "check_id": check.id,
            "application_id": check.application_id,
            "status": status_value,
            "check_types": check.check_types,
            "results": check.results if hasattr(check, 'results') else {},
            "flags": check.flags if hasattr(check, 'flags') else [],
            "overall_assessment": check.overall_assessment if hasattr(check, 'overall_assessment') else None,
            "completed_at": check.completed_at.isoformat() if hasattr(check, 'completed_at') and check.completed_at else None,
            "report_url": check.report_url if hasattr(check, 'report_url') else None,
        }
