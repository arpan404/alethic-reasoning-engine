"""Background check integration tools for Alethic agents.

These tools handle external API calls for background check services.
Only tools that require external system integration are included here.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.background_checks import BackgroundCheck, BackgroundCheckResult
from database.models.applications import Application
from agents.tools.queue import enqueue_task

logger = logging.getLogger(__name__)


# Supported background check types
BACKGROUND_CHECK_TYPES = [
    "criminal",
    "employment",
    "education",
    "credit",
    "drug_screening",
    "professional_license",
    "motor_vehicle",
    "social_security",
]


async def initiate_background_check(
    application_id: int,
    check_types: List[str],
    provider: str = "default",
    priority: str = "normal",
    initiated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Initiate a background check request with external provider.
    
    Multi-tenant safe: Operates through application context.
    This queues a request to the background check API service.
    
    Args:
        application_id: The application (provides org scoping)
        check_types: Types of checks to run (criminal, employment, education, etc.)
        provider: Background check provider (checkr, sterling, etc.)
        priority: Processing priority
        initiated_by: User ID who initiated
        
    Returns:
        Dictionary with check request ID and status
    """
    # Validate check types
    invalid_types = [t for t in check_types if t not in BACKGROUND_CHECK_TYPES]
    if invalid_types:
        return {
            "success": False,
            "error": f"Invalid check types: {invalid_types}. Valid types: {BACKGROUND_CHECK_TYPES}",
        }
    
    if not check_types:
        return {
            "success": False,
            "error": "At least one check type is required",
        }
    
    # Get candidate_id from application
    async with AsyncSessionLocal() as session:
        query = select(Application).where(Application.id == application_id)
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application {application_id} not found",
            }
        
        candidate_id = app.candidate_id
    
    # Generate request ID
    request_id = f"bgc_{uuid.uuid4().hex[:12]}"
    
    # Queue the background check task
    task_result = await enqueue_task(
        task_type="initiate_background_check",
        payload={
            "request_id": request_id,
            "application_id": application_id,
            "candidate_id": candidate_id,
            "check_types": check_types,
            "provider": provider,
            "initiated_by": initiated_by,
        },
        priority=priority,
    )
    
    logger.info(
        f"Initiated background check {request_id} for application {application_id}: "
        f"{check_types}"
    )
    
    return {
        "success": True,
        "request_id": request_id,
        "application_id": application_id,
        "check_types": check_types,
        "provider": provider,
        "status": "initiated",
        "task_id": task_result.get("task_id"),
        "message": "Background check initiated. Results typically available in 24-72 hours.",
    }


async def track_background_check_status(
    request_id: str,
) -> Dict[str, Any]:
    """Track the status of a background check request.
    
    Queries the external provider API for current status.
    
    Args:
        request_id: The background check request ID
        
    Returns:
        Dictionary with current status and available results
    """
    # In production, this would call the external provider API
    # For now, we return a mock status structure
    
    # This would typically be a database lookup + API call
    
    async with AsyncSessionLocal() as session:
        query = select(BackgroundCheck).where(
            BackgroundCheck.request_id == request_id
        )
        result = await session.execute(query)
        check = result.scalar_one_or_none()
        
        if not check:
            return {
                "found": False,
                "error": f"Background check {request_id} not found",
            }
        
        return {
            "found": True,
            "request_id": request_id,
            "candidate_id": check.candidate_id,
            "application_id": check.application_id,
            "status": check.status,
            "check_types": check.check_types or [],
            "provider": check.provider,
            "initiated_at": check.created_at.isoformat() if check.created_at else None,
            "completed_at": check.completed_at.isoformat() if check.completed_at else None,
            "result_summary": check.result_summary,
            "has_flags": check.has_flags,
            "flag_count": check.flag_count or 0,
        }


async def get_background_check_results(
    request_id: str,
) -> Dict[str, Any]:
    """Get detailed results of a completed background check.
    
    Args:
        request_id: The background check request ID
        
    Returns:
        Dictionary with detailed check results
    """
    
    async with AsyncSessionLocal() as session:
        query = (
            select(BackgroundCheck)
            .options(selectinload(BackgroundCheck.results))
            .where(BackgroundCheck.request_id == request_id)
        )
        result = await session.execute(query)
        check = result.scalar_one_or_none()
        
        if not check:
            return {
                "found": False,
                "error": f"Background check {request_id} not found",
            }
        
        if check.status != "completed":
            return {
                "found": True,
                "request_id": request_id,
                "status": check.status,
                "message": "Background check is not yet completed",
            }
        
        # Build results by check type
        results_by_type = {}
        for r in (check.results or []):
            results_by_type[r.check_type] = {
                "status": r.status,
                "passed": r.passed,
                "flags": r.flags or [],
                "details": r.details,
                "verified_at": r.verified_at.isoformat() if r.verified_at else None,
            }
        
        return {
            "found": True,
            "request_id": request_id,
            "candidate_id": check.candidate_id,
            "application_id": check.application_id,
            "status": check.status,
            "completed_at": check.completed_at.isoformat() if check.completed_at else None,
            "overall_passed": check.overall_passed,
            "has_flags": check.has_flags,
            "results": results_by_type,
            "summary": check.result_summary,
        }
