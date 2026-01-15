"""
Calendar service functions for API endpoints.

Provides direct database operations for calendar and scheduling,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.calendar import CalendarEvent, UserCalendar
from database.models.users import User

logger = logging.getLogger(__name__)


async def get_user_availability(
    user_ids: List[int],
    date: str,
) -> Dict[str, Any]:
    """
    Get availability for specified users on a date.
    
    Args:
        user_ids: User IDs to check
        date: Date to check (YYYY-MM-DD)
        
    Returns:
        Dictionary with availability data
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    async with AsyncSessionLocal() as session:
        availability = {}
        
        for user_id in user_ids:
            # Get user's events for the day
            result = await session.execute(
                select(CalendarEvent)
                .where(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time >= start_of_day,
                    CalendarEvent.end_time <= end_of_day,
                )
                .order_by(CalendarEvent.start_time)
            )
            events = result.scalars().all()
            
            busy_slots = []
            for event in events:
                busy_slots.append({
                    "start": event.start_time.isoformat() if event.start_time else None,
                    "end": event.end_time.isoformat() if event.end_time else None,
                    "title": event.title,
                })
            
            # Calculate available slots (simplified: 9 AM - 6 PM)
            work_start = start_of_day.replace(hour=9)
            work_end = start_of_day.replace(hour=18)
            
            available_slots = []
            current_time = work_start
            
            for busy in busy_slots:
                busy_start = datetime.fromisoformat(busy["start"]) if busy["start"] else current_time
                if current_time < busy_start:
                    available_slots.append({
                        "start": current_time.isoformat(),
                        "end": busy_start.isoformat(),
                    })
                busy_end = datetime.fromisoformat(busy["end"]) if busy["end"] else busy_start
                current_time = max(current_time, busy_end)
            
            if current_time < work_end:
                available_slots.append({
                    "start": current_time.isoformat(),
                    "end": work_end.isoformat(),
                })
            
            availability[str(user_id)] = {
                "busy_slots": busy_slots,
                "available_slots": available_slots,
            }
        
        return {
            "date": date,
            "users": availability,
        }


async def find_available_slots(
    user_ids: List[int],
    date: str,
    duration_minutes: int = 60,
) -> Dict[str, Any]:
    """
    Find common available time slots for multiple users.
    
    Args:
        user_ids: User IDs who must be available
        date: Date to find slots (YYYY-MM-DD)
        duration_minutes: Required meeting duration
        
    Returns:
        Dictionary with available slot options
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    # Get availability for all users
    availability_result = await get_user_availability(user_ids, date)
    
    if "error" in availability_result:
        return availability_result
    
    # Find overlapping available slots
    all_available = []
    
    for user_id, user_data in availability_result.get("users", {}).items():
        slots = user_data.get("available_slots", [])
        if not all_available:
            all_available = slots
        else:
            # Intersect with previous slots
            new_available = []
            for slot in all_available:
                slot_start = datetime.fromisoformat(slot["start"])
                slot_end = datetime.fromisoformat(slot["end"])
                
                for other in slots:
                    other_start = datetime.fromisoformat(other["start"])
                    other_end = datetime.fromisoformat(other["end"])
                    
                    # Find intersection
                    intersect_start = max(slot_start, other_start)
                    intersect_end = min(slot_end, other_end)
                    
                    if intersect_start < intersect_end:
                        new_available.append({
                            "start": intersect_start.isoformat(),
                            "end": intersect_end.isoformat(),
                        })
            
            all_available = new_available
    
    # Filter slots that fit the required duration
    duration = timedelta(minutes=duration_minutes)
    valid_slots = []
    
    for slot in all_available:
        slot_start = datetime.fromisoformat(slot["start"])
        slot_end = datetime.fromisoformat(slot["end"])
        
        if slot_end - slot_start >= duration:
            valid_slots.append({
                "start": slot["start"],
                "end": slot["end"],
                "duration_available": int((slot_end - slot_start).total_seconds() / 60),
            })
    
    return {
        "date": date,
        "duration_required": duration_minutes,
        "users": user_ids,
        "available_slots": valid_slots,
        "total_slots": len(valid_slots),
    }


async def create_calendar_event(
    title: str,
    start_time: datetime,
    end_time: datetime,
    attendees: List[str],
    location: Optional[str] = None,
    description: Optional[str] = None,
    send_invites: bool = True,
    created_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a calendar event.
    
    Args:
        title: Event title
        start_time: Event start datetime
        end_time: Event end datetime
        attendees: List of attendee email addresses
        location: Event location
        description: Event description
        send_invites: Whether to send calendar invites
        created_by: User ID who created the event
        
    Returns:
        Dictionary with event details
    """
    async with AsyncSessionLocal() as session:
        event = CalendarEvent(
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            description=description,
            user_id=created_by,
        )
        session.add(event)
        await session.flush()
        
        # Queue invite emails if requested
        invite_status = "not_sent"
        if send_invites and attendees:
            try:
                from workers.tasks import queue_calendar_invites
                await queue_calendar_invites(event.id, attendees)
                invite_status = "queued"
            except Exception as e:
                logger.warning(f"Failed to queue calendar invites: {e}")
                invite_status = "failed"
        
        await session.commit()
        
        return {
            "success": True,
            "event_id": event.id,
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "location": location,
            "attendees": attendees,
            "invite_status": invite_status,
        }
