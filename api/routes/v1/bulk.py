"""Bulk operations API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import bulk as bulk_service

router = APIRouter(prefix="/bulk", tags=["bulk"])


class BulkUploadRequest(BaseModel):
    job_id: int
    file_urls: List[str] = Field(..., min_length=1, max_length=100)
    source: str = Field(default="bulk_upload")


class BulkRejectRequest(BaseModel):
    application_ids: List[int] = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=5)
    send_notification: bool = True


class BulkMoveStageRequest(BaseModel):
    application_ids: List[int] = Field(..., min_length=1, max_length=100)
    new_stage: str
    reason: Optional[str] = None


@router.post("/upload-resumes")
async def upload_resumes_bulk(
    request: BulkUploadRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Bulk upload resumes for a job.
    
    Accepts a list of file URLs to process asynchronously.
    Returns a task ID for tracking progress.
    """
    result = await bulk_service.upload_resumes_bulk(
        job_id=request.job_id,
        file_paths=request.file_urls,
        source=request.source,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/upload-status/{task_id}")
async def get_bulk_upload_status(
    task_id: str = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get status of a bulk upload task."""
    result = await bulk_service.get_bulk_upload_status(task_id)
    return result


@router.post("/reject")
async def bulk_reject_candidates(
    request: BulkRejectRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Reject multiple candidates at once.
    
    Optionally sends rejection notifications.
    """
    result = await bulk_service.bulk_reject_candidates(
        application_ids=request.application_ids,
        reason=request.reason,
        send_notification=request.send_notification,
        rejected_by=current_user.id,
    )
    return result


@router.post("/move-stage")
async def bulk_move_stage(
    request: BulkMoveStageRequest,
    current_user: User = Depends(require_active_user),
):
    """Move multiple applications to a new stage."""
    result = await bulk_service.bulk_move_stage(
        application_ids=request.application_ids,
        new_stage=request.new_stage,
        reason=request.reason,
        moved_by=current_user.id,
    )
    return result
