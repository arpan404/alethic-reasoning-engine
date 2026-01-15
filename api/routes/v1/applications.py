"""
Application workflow management endpoints.

Provides REST API for viewing applications and moving them through pipeline stages.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import applications as application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get(
    "/{application_id}",
    summary="Get Application Details",
    description="Get detailed application information. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_application(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve complete application details including candidate info and AI scores."""
    result = await application_service.get_application(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.post(
    "/{application_id}/move-stage",
    summary="Move Application Stage",
    description="Move application to a different pipeline stage. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def move_application_stage(
    application_id: int = Path(..., description="Application ID"),
    stage: str = Body(..., embed=True, description="Target pipeline stage"),
    reason: str = Body(None, embed=True, description="Reason for stage change"),
    current_user: User = Depends(require_active_user),
):
    """Move an application to a new stage in the hiring pipeline."""
    result = await application_service.move_application_stage(
        application_id=application_id,
        new_stage=stage,
        reason=reason,
        moved_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to move stage"))
    
    return result


@router.get(
    "",
    summary="List Applications",
    description="List applications for a job with filtering. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def list_applications(
    job_id: int = Query(..., description="Job ID to list applications for"),
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_shortlisted: Optional[bool] = Query(None, description="Filter shortlisted only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of applications for a job."""
    return await application_service.list_applications(
        job_id=job_id,
        stage=stage,
        status=status,
        is_shortlisted=is_shortlisted,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{application_id}/history",
    summary="Get Application History",
    description="Get activity history for an application. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_application_history(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve complete activity and note history for an application."""
    return await application_service.get_application_history(application_id)
