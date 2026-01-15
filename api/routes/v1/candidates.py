"""Candidate management API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import candidates as candidate_service

router = APIRouter(prefix="/candidates", tags=["candidates"])


class ShortlistRequest(BaseModel):
    reason: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=5)
    send_notification: bool = True


@router.get("")
async def list_candidates(
    job_id: int = Query(..., description="Job ID to list candidates for"),
    stage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by name or email"),
    is_shortlisted: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """List candidates for a job with filtering."""
    result = await candidate_service.list_candidates(
        job_id=job_id,
        stage=stage,
        status=status,
        search_query=search,
        is_shortlisted=is_shortlisted,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/{application_id}")
async def get_candidate(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Get detailed candidate information."""
    result = await candidate_service.get_candidate(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return result


@router.post("/{application_id}/shortlist")
async def shortlist_candidate(
    application_id: int = Path(...),
    request: ShortlistRequest = Body(default=ShortlistRequest()),
    current_user: User = Depends(require_active_user),
):
    """Shortlist a candidate."""
    result = await candidate_service.shortlist_candidate(
        application_id=application_id,
        reason=request.reason,
        shortlisted_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{application_id}/reject")
async def reject_candidate(
    application_id: int = Path(...),
    request: RejectRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Reject a candidate."""
    result = await candidate_service.reject_candidate(
        application_id=application_id,
        reason=request.reason,
        send_notification=request.send_notification,
        rejected_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{application_id}/documents")
async def get_candidate_documents(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get all documents for a candidate."""
    result = await candidate_service.get_candidate_documents(application_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
