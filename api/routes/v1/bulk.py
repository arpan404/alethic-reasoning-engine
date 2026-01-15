"""
Bulk operations endpoints.

Provides REST API for batch processing of candidates and applications.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import bulk as bulk_service

router = APIRouter(prefix="/bulk", tags=["bulk"])


class BulkUploadRequest(BaseModel):
    """Request model for bulk resume upload."""
    job_id: int = Field(..., description="Job to upload resumes for")
    file_paths: list[str] = Field(..., min_length=1, description="Paths to uploaded resume files")
    source: str = Field("bulk_upload", description="Application source tracking")


class BulkRejectRequest(BaseModel):
    """Request model for bulk rejection."""
    application_ids: list[int] = Field(..., min_length=1, description="Application IDs to reject")
    reason: str = Field(..., min_length=5, description="Rejection reason")
    send_notification: bool = Field(True, description="Send rejection emails")


class BulkMoveStageRequest(BaseModel):
    """Request model for bulk stage move."""
    application_ids: list[int] = Field(..., min_length=1, description="Application IDs to move")
    stage: str = Field(..., description="Target pipeline stage")
    reason: Optional[str] = Field(None, description="Reason for stage change")


@router.post(
    "/upload-resumes",
    summary="Bulk Upload Resumes",
    description="Upload multiple resumes for processing. Requires candidate:create permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_CREATE))],
)
async def upload_resumes_bulk(
    request: BulkUploadRequest,
    current_user: User = Depends(require_active_user),
):
    """Queue multiple resumes for parsing and application creation."""
    result = await bulk_service.upload_resumes_bulk(
        job_id=request.job_id,
        file_paths=request.file_paths,
        source=request.source,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "/upload-status/{task_id}",
    summary="Get Bulk Upload Status",
    description="Check status of a bulk upload task. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_bulk_upload_status(
    task_id: str = Path(..., description="Bulk upload task ID"),
    current_user: User = Depends(require_active_user),
):
    """Get progress and results of a bulk upload operation."""
    return await bulk_service.get_bulk_upload_status(task_id)


@router.post(
    "/reject",
    summary="Bulk Reject Candidates",
    description="Reject multiple candidates at once. Requires application:reject permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_REJECT))],
)
async def bulk_reject_candidates(
    request: BulkRejectRequest,
    current_user: User = Depends(require_active_user),
):
    """Reject multiple applications in a single operation."""
    if len(request.application_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 applications per request")
    
    return await bulk_service.bulk_reject_candidates(
        application_ids=request.application_ids,
        reason=request.reason,
        send_notification=request.send_notification,
        rejected_by=current_user.id,
    )


@router.post(
    "/move-stage",
    summary="Bulk Move Stage",
    description="Move multiple applications to a new stage. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def bulk_move_stage(
    request: BulkMoveStageRequest,
    current_user: User = Depends(require_active_user),
):
    """Move multiple applications to a new pipeline stage."""
    if len(request.application_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 applications per request")
    
    return await bulk_service.bulk_move_stage(
        application_ids=request.application_ids,
        new_stage=request.stage,
        reason=request.reason,
        moved_by=current_user.id,
    )
