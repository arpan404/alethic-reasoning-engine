"""Interview management API routes."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Body, HTTPException, Path
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import interviews as interview_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


class InterviewScheduleRequest(BaseModel):
    application_id: int
    interview_type: str = Field(..., description="Type of interview (e.g. 'phone', 'technical')")
    scheduled_at: datetime = Field(..., description="ISO formatted date time")
    duration_minutes: int = Field(60, ge=15, le=480)
    interviewer_ids: List[int] = Field(default=[], description="List of interviewer User IDs")
    location: Optional[str] = None
    notes: Optional[str] = None


class RescheduleRequest(BaseModel):
    new_datetime: datetime
    reason: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/schedule")
async def schedule_interview(
    request: InterviewScheduleRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Schedule an interview for an application.
    """
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
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to schedule interview"))
        
    return result


@router.get("")
async def list_interviews(
    application_id: Optional[int] = Query(None),
    job_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """
    List interviews with filtering.
    """
    result = await interview_service.list_interviews(
        application_id=application_id,
        job_id=job_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    
    return result


@router.get("/{interview_id}")
async def get_interview(
    interview_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get interview details."""
    result = await interview_service.get_interview(interview_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interview not found")
    return result


@router.post("/{interview_id}/reschedule")
async def reschedule_interview(
    interview_id: int = Path(...),
    request: RescheduleRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Reschedule an interview."""
    result = await interview_service.reschedule_interview(
        interview_id=interview_id,
        new_datetime=request.new_datetime,
        reason=request.reason,
        rescheduled_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{interview_id}/cancel")
async def cancel_interview(
    interview_id: int = Path(...),
    request: CancelRequest = Body(default=CancelRequest()),
    current_user: User = Depends(require_active_user),
):
    """Cancel an interview."""
    result = await interview_service.cancel_interview(
        interview_id=interview_id,
        reason=request.reason,
        cancelled_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
