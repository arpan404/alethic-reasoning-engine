"""Application management API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query
from api.dependencies import require_active_user
from database.models.users import User
from api.services import applications as application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/{application_id}")
async def get_application(
    application_id: int = Path(..., description="The ID of the application to retrieve"),
    current_user: User = Depends(require_active_user),
):
    """
    Get detailed information about an application.
    """
    result = await application_service.get_application(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.post("/{application_id}/move-stage")
async def move_application_stage(
    application_id: int = Path(...),
    stage: str = Body(..., embed=True),
    reason: str = Body(None, embed=True),
    current_user: User = Depends(require_active_user),
):
    """
    Move an application to a different stage.
    """
    result = await application_service.move_application_stage(
        application_id=application_id,
        new_stage=stage,
        reason=reason,
        moved_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to move stage"))
        
    return result


@router.get("")
async def list_applications(
    job_id: int = Query(..., description="Job ID to list applications for"),
    stage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_shortlisted: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """List applications for a job with filtering."""
    result = await application_service.list_applications(
        job_id=job_id,
        stage=stage,
        status=status,
        is_shortlisted=is_shortlisted,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/{application_id}/history")
async def get_application_history(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get full activity history for an application."""
    result = await application_service.get_application_history(application_id)
    return result
