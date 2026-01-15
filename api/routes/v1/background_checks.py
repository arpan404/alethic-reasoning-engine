"""Background checks API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import background_checks as bg_check_service

router = APIRouter(prefix="/background-checks", tags=["background-checks"])


class InitiateCheckRequest(BaseModel):
    application_id: int
    check_types: List[str] = Field(
        ...,
        min_length=1,
        description="Types of checks: criminal, employment, education, credit"
    )
    priority: str = Field(default="normal", pattern="^(normal|rush)$")


@router.post("/initiate")
async def initiate_background_check(
    request: InitiateCheckRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Initiate a background check for an application.
    
    Starts the background check process with the specified check types.
    """
    valid_types = {"criminal", "employment", "education", "credit", "identity", "reference"}
    invalid_types = [t for t in request.check_types if t not in valid_types]
    if invalid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid check types: {invalid_types}"
        )
    
    result = await bg_check_service.initiate_background_check(
        application_id=request.application_id,
        check_types=request.check_types,
        priority=request.priority,
        initiated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{check_id}/status")
async def get_background_check_status(
    check_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get status of a background check."""
    result = await bg_check_service.get_background_check_status(check_id)
    if not result:
        raise HTTPException(status_code=404, detail="Background check not found")
    return result


@router.get("/{check_id}/results")
async def get_background_check_results(
    check_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """
    Get results of a completed background check.
    
    Results are only available after the check is completed.
    """
    result = await bg_check_service.get_background_check_results(check_id)
    if not result:
        raise HTTPException(status_code=404, detail="Background check not found")
    return result
