"""
Interview scheduling and management endpoints.

Provides REST API for scheduling, listing, rescheduling, and cancelling interviews.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Body, HTTPException, Path
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import interviews as interview_service

router = APIRouter(prefix="/interviews", tags=["interviews"])


class InterviewScheduleRequest(BaseModel):
    """Request model for scheduling an interview."""
    application_id: int = Field(..., description="Application to schedule interview for")
    interview_type: str = Field(..., description="Type: phone, technical, onsite, panel")
    scheduled_at: datetime = Field(..., description="Interview date and time (ISO 8601)")
    duration_minutes: int = Field(60, ge=15, le=480, description="Duration in minutes")
    interviewer_ids: list[int] = Field(default=[], description="Interviewer user IDs")
    location: Optional[str] = Field(None, description="Interview location or meeting link")
    notes: Optional[str] = Field(None, description="Private notes for interviewers")


class RescheduleRequest(BaseModel):
    """Request model for rescheduling an interview."""
    new_datetime: datetime = Field(..., description="New interview date and time")
    reason: Optional[str] = Field(None, description="Reason for rescheduling")


class CancelRequest(BaseModel):
    """Request model for cancelling an interview."""
    reason: Optional[str] = Field(None, description="Reason for cancellation")


@router.post(
    "/schedule",
    summary="Schedule Interview",
    description="Schedule a new interview for an application. Requires interview:schedule permission.",
    dependencies=[Depends(require_permission(Permission.INTERVIEW_SCHEDULE))],
)
async def schedule_interview(
    request: InterviewScheduleRequest,
    current_user: User = Depends(require_active_user),
):
    """Schedule a new interview for a candidate application."""
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


@router.get(
    "",
    summary="List Interviews",
    description="List interviews with optional filtering. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def list_interviews(
    application_id: Optional[int] = Query(None, description="Filter by application"),
    job_id: Optional[int] = Query(None, description="Filter by job"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of interviews with optional filters."""
    return await interview_service.list_interviews(
        application_id=application_id,
        job_id=job_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{interview_id}",
    summary="Get Interview Details",
    description="Get details of a specific interview. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_interview(
    interview_id: int = Path(..., description="Interview ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve detailed information about an interview."""
    result = await interview_service.get_interview(interview_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interview not found")
    return result


@router.post(
    "/{interview_id}/reschedule",
    summary="Reschedule Interview",
    description="Reschedule an existing interview. Requires interview:schedule permission.",
    dependencies=[Depends(require_permission(Permission.INTERVIEW_SCHEDULE))],
)
async def reschedule_interview(
    interview_id: int = Path(..., description="Interview ID"),
    request: RescheduleRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Reschedule an interview to a new date and time."""
    result = await interview_service.reschedule_interview(
        interview_id=interview_id,
        new_datetime=request.new_datetime,
        reason=request.reason,
        rescheduled_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/{interview_id}/cancel",
    summary="Cancel Interview",
    description="Cancel a scheduled interview. Requires interview:schedule permission.",
    dependencies=[Depends(require_permission(Permission.INTERVIEW_SCHEDULE))],
)
async def cancel_interview(
    interview_id: int = Path(..., description="Interview ID"),
    request: CancelRequest = Body(default=CancelRequest()),
    current_user: User = Depends(require_active_user),
):
    """Cancel a scheduled interview."""
    result = await interview_service.cancel_interview(
        interview_id=interview_id,
        reason=request.reason,
        cancelled_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
