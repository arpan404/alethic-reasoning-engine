"""Calendar API routes."""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import calendar as calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


class AvailabilityRequest(BaseModel):
    user_ids: List[int] = Field(..., min_length=1)
    date: str = Field(..., description="Date in YYYY-MM-DD format")


class FindSlotsRequest(BaseModel):
    user_ids: List[int] = Field(..., min_length=1)
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    duration_minutes: int = Field(default=60, ge=15, le=480)


class CreateEventRequest(BaseModel):
    title: str = Field(..., max_length=200)
    start_time: datetime
    end_time: datetime
    attendees: List[str] = Field(default=[], description="Attendee email addresses")
    location: Optional[str] = None
    description: Optional[str] = None
    send_invites: bool = True


@router.post("/availability")
async def get_user_availability(
    request: AvailabilityRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Get availability for specified users on a date.
    
    Returns busy and available time slots.
    """
    result = await calendar_service.get_user_availability(
        user_ids=request.user_ids,
        date=request.date,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/find-slots")
async def find_available_slots(
    request: FindSlotsRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Find common available time slots for multiple users.
    
    Returns slots where all users are available for the requested duration.
    """
    result = await calendar_service.find_available_slots(
        user_ids=request.user_ids,
        date=request.date,
        duration_minutes=request.duration_minutes,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/events")
async def create_calendar_event(
    request: CreateEventRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Create a calendar event.
    
    Optionally sends calendar invites to attendees.
    """
    if request.end_time <= request.start_time:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    result = await calendar_service.create_calendar_event(
        title=request.title,
        start_time=request.start_time,
        end_time=request.end_time,
        attendees=request.attendees,
        location=request.location,
        description=request.description,
        send_invites=request.send_invites,
        created_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
