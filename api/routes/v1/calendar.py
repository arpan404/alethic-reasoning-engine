"""
Calendar and scheduling endpoints.

Provides REST API for checking availability and scheduling events.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import calendar as calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


class CreateEventRequest(BaseModel):
    """Request model for creating a calendar event."""
    title: str = Field(..., min_length=2, description="Event title")
    start_time: datetime = Field(..., description="Event start time (ISO 8601)")
    end_time: datetime = Field(..., description="Event end time (ISO 8601)")
    attendees: list[str] = Field(default=[], description="Attendee email addresses")
    location: Optional[str] = Field(None, description="Event location or meeting link")
    description: Optional[str] = Field(None, description="Event description")
    send_invites: bool = Field(True, description="Send calendar invites to attendees")


@router.get(
    "/availability",
    summary="Get User Availability",
    description="Get availability for users on a specific date. Requires interview:schedule permission.",
    dependencies=[Depends(require_permission(Permission.INTERVIEW_SCHEDULE))],
)
async def get_user_availability(
    user_ids: str = Query(..., description="Comma-separated user IDs"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(require_active_user),
):
    """Get busy and available time slots for specified users on a date."""
    try:
        ids = [int(id.strip()) for id in user_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    result = await calendar_service.get_user_availability(user_ids=ids, date=date)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get(
    "/slots",
    summary="Find Available Slots",
    description="Find common available slots for multiple users. Requires interview:schedule permission.",
    dependencies=[Depends(require_permission(Permission.INTERVIEW_SCHEDULE))],
)
async def find_available_slots(
    user_ids: str = Query(..., description="Comma-separated user IDs"),
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    duration: int = Query(60, ge=15, le=480, description="Required duration in minutes"),
    current_user: User = Depends(require_active_user),
):
    """Find overlapping available time slots that fit the required duration."""
    try:
        ids = [int(id.strip()) for id in user_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")
    
    result = await calendar_service.find_available_slots(
        user_ids=ids,
        date=date,
        duration_minutes=duration,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/events",
    summary="Create Calendar Event",
    description="Create a new calendar event. Requires interview:schedule permission.",
    dependencies=[Depends(require_permission(Permission.INTERVIEW_SCHEDULE))],
)
async def create_calendar_event(
    request: CreateEventRequest,
    current_user: User = Depends(require_active_user),
):
    """Create a calendar event and optionally send invites to attendees."""
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
