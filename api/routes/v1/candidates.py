"""
Candidate management endpoints.

Provides REST API for listing, viewing, shortlisting, and rejecting candidates.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import candidates as candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


class ShortlistRequest(BaseModel):
    """Request model for shortlisting a candidate."""
    reason: Optional[str] = Field(None, description="Reason for shortlisting")


class RejectRequest(BaseModel):
    """Request model for rejecting a candidate."""
    reason: str = Field(..., min_length=5, description="Reason for rejection (required)")
    send_notification: bool = Field(True, description="Send rejection email to candidate")


@router.get(
    "",
    summary="List Candidates",
    description="List candidates for a job with optional filtering. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def list_candidates(
    job_id: int = Query(..., description="Job ID to list candidates for"),
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_shortlisted: Optional[bool] = Query(None, description="Filter shortlisted only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of candidates for a job."""
    return await candidate_service.list_candidates(
        job_id=job_id,
        stage=stage,
        status=status,
        search_query=search,
        is_shortlisted=is_shortlisted,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{application_id}",
    summary="Get Candidate Details",
    description="Get detailed candidate information via application ID. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_candidate(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve complete candidate profile and application details."""
    result = await candidate_service.get_candidate(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result


@router.post(
    "/{application_id}/shortlist",
    summary="Shortlist Candidate",
    description="Add candidate to shortlist. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def shortlist_candidate(
    application_id: int = Path(..., description="Application ID"),
    request: ShortlistRequest = Body(default=ShortlistRequest()),
    current_user: User = Depends(require_active_user),
):
    """Add a candidate to the shortlist for further consideration."""
    result = await candidate_service.shortlist_candidate(
        application_id=application_id,
        reason=request.reason,
        shortlisted_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/{application_id}/reject",
    summary="Reject Candidate",
    description="Reject a candidate's application. Requires application:reject permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_REJECT))],
)
async def reject_candidate(
    application_id: int = Path(..., description="Application ID"),
    request: RejectRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Reject a candidate's application with optional notification."""
    result = await candidate_service.reject_candidate(
        application_id=application_id,
        reason=request.reason,
        send_notification=request.send_notification,
        rejected_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "/{application_id}/documents",
    summary="Get Candidate Documents",
    description="Get all documents for a candidate. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_candidate_documents(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve all documents (resume, cover letter, etc.) for a candidate."""
    result = await candidate_service.get_candidate_documents(application_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
