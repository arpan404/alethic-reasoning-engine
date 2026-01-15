"""
Background check endpoints.

Provides REST API for initiating and tracking employment background checks.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import background_checks as bgcheck_service

router = APIRouter(prefix="/background-checks", tags=["background-checks"])


class InitiateCheckRequest(BaseModel):
    """Request model for initiating a background check."""
    application_id: int = Field(..., description="Application to run check for")
    check_types: list[str] = Field(
        ...,
        min_length=1,
        description="Types: criminal, employment, education, credit, identity"
    )
    priority: str = Field("normal", description="Priority: normal, high, urgent")


@router.post(
    "",
    summary="Initiate Background Check",
    description="Start a background check for a candidate. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def initiate_background_check(
    request: InitiateCheckRequest,
    current_user: User = Depends(require_active_user),
):
    """Initiate a background verification check with selected check types."""
    valid_types = {"criminal", "employment", "education", "credit", "identity"}
    invalid = set(request.check_types) - valid_types
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid check types: {invalid}. Valid: {valid_types}"
        )
    
    result = await bgcheck_service.initiate_background_check(
        application_id=request.application_id,
        check_types=request.check_types,
        priority=request.priority,
        initiated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "/{check_id}/status",
    summary="Get Background Check Status",
    description="Get current status of a background check. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_background_check_status(
    check_id: int = Path(..., description="Background check ID"),
    current_user: User = Depends(require_active_user),
):
    """Get the current status and progress of a background check."""
    result = await bgcheck_service.get_background_check_status(check_id)
    if not result:
        raise HTTPException(status_code=404, detail="Background check not found")
    return result


@router.get(
    "/{check_id}/results",
    summary="Get Background Check Results",
    description="Get results of a completed background check. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_background_check_results(
    check_id: int = Path(..., description="Background check ID"),
    current_user: User = Depends(require_active_user),
):
    """Get detailed results and findings from a completed background check."""
    result = await bgcheck_service.get_background_check_results(check_id)
    if not result:
        raise HTTPException(status_code=404, detail="Background check not found")
    return result
