"""Direct actions API routes.

This file provides quick action endpoints that call the appropriate services.
These are convenience endpoints for common actions.
"""

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import (
    candidates as candidate_service,
    applications as application_service,
    interviews as interview_service,
    evaluations as evaluation_service,
)

router = APIRouter(prefix="/actions", tags=["actions"])


# Request models

class ShortlistRequest(BaseModel):
    application_id: int
    reason: Optional[str] = None


class RejectRequest(BaseModel):
    application_id: int
    reason: str = Field(..., min_length=5)
    send_notification: bool = True


class MoveStageRequest(BaseModel):
    application_id: int
    stage: str
    reason: Optional[str] = None


class ScheduleInterviewRequest(BaseModel):
    application_id: int
    interview_type: str
    scheduled_at: datetime
    duration_minutes: int = 60
    interviewer_ids: List[int] = []
    location: Optional[str] = None
    notes: Optional[str] = None


class TriggerEvaluationRequest(BaseModel):
    application_id: int
    evaluation_type: str = Field(default="pre", pattern="^(pre|full)$")


# Action endpoints

@router.post("/shortlist")
async def shortlist_candidate(
    request: ShortlistRequest,
    current_user: User = Depends(require_active_user),
):
    """Quick action to shortlist a candidate."""
    result = await candidate_service.shortlist_candidate(
        application_id=request.application_id,
        reason=request.reason,
        shortlisted_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/reject")
async def reject_candidate(
    request: RejectRequest,
    current_user: User = Depends(require_active_user),
):
    """Quick action to reject a candidate."""
    result = await candidate_service.reject_candidate(
        application_id=request.application_id,
        reason=request.reason,
        send_notification=request.send_notification,
        rejected_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/move-stage")
async def move_stage(
    request: MoveStageRequest,
    current_user: User = Depends(require_active_user),
):
    """Quick action to move an application to a different stage."""
    result = await application_service.move_application_stage(
        application_id=request.application_id,
        new_stage=request.stage,
        reason=request.reason,
        moved_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/schedule-interview")
async def schedule_interview(
    request: ScheduleInterviewRequest,
    current_user: User = Depends(require_active_user),
):
    """Quick action to schedule an interview."""
    interviewer_ids = request.interviewer_ids or [current_user.id]
    
    result = await interview_service.schedule_interview(
        application_id=request.application_id,
        interview_type=request.interview_type,
        scheduled_at=request.scheduled_at,
        duration_minutes=request.duration_minutes,
        interviewer_ids=interviewer_ids,
        location=request.location,
        notes=request.notes,
        scheduled_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/trigger-evaluation")
async def trigger_evaluation(
    request: TriggerEvaluationRequest,
    current_user: User = Depends(require_active_user),
):
    """Quick action to trigger an AI evaluation."""
    result = await evaluation_service.trigger_evaluation(
        application_id=request.application_id,
        evaluation_type=request.evaluation_type,
        requested_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
