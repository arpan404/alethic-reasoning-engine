"""Calendar service functions."""

from typing import Any, Optional
from datetime import datetime, timedelta
import logging

from sqlalchemy import select

from database.engine import AsyncSessionLocal
from database.models.calendar import CalendarEvent, UserCalendar
from database.models.users import User

logger = logging.getLogger(__name__)


async def get_user_availability(
    user_ids: list[int],
    date: str,
) -> dict[str, Any]:
    """Get availability for users on a date."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    async with AsyncSessionLocal() as session:
        availability: dict[str, Any] = {}
        
        for user_id in user_ids:
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
            
            busy_slots: list[dict[str, Any]] = []
            for event in events:
                busy_slots.append({
                    "start": event.start_time.isoformat() if event.start_time else None,
                    "end": event.end_time.isoformat() if event.end_time else None,
                    "title": event.title,
                })
            
            work_start = start_of_day.replace(hour=9)
            work_end = start_of_day.replace(hour=18)
            
            available_slots: list[dict[str, str]] = []
            current_time = work_start
            
            for busy in busy_slots:
                busy_start_str = busy.get("start")
                busy_end_str = busy.get("end")
                busy_start = datetime.fromisoformat(busy_start_str) if busy_start_str else current_time
                if current_time < busy_start:
                    available_slots.append({
                        "start": current_time.isoformat(),
                        "end": busy_start.isoformat(),
                    })
                busy_end = datetime.fromisoformat(busy_end_str) if busy_end_str else busy_start
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
        
        return {"date": date, "users": availability}


async def find_available_slots(
    user_ids: list[int],
    date: str,
    duration_minutes: int = 60,
) -> dict[str, Any]:
    """Find common available slots for multiple users."""
    try:
        datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    availability_result = await get_user_availability(user_ids, date)
    
    if "error" in availability_result:
        return availability_result
    
    all_available: list[dict[str, str]] = []
    
    for user_id, user_data in availability_result.get("users", {}).items():
        slots = user_data.get("available_slots", [])
        if not all_available:
            all_available = slots
        else:
            new_available: list[dict[str, str]] = []
            for slot in all_available:
                slot_start = datetime.fromisoformat(slot["start"])
                slot_end = datetime.fromisoformat(slot["end"])
                
                for other in slots:
                    other_start = datetime.fromisoformat(other["start"])
                    other_end = datetime.fromisoformat(other["end"])
                    
                    intersect_start = max(slot_start, other_start)
                    intersect_end = min(slot_end, other_end)
                    
                    if intersect_start < intersect_end:
                        new_available.append({
                            "start": intersect_start.isoformat(),
                            "end": intersect_end.isoformat(),
                        })
            
            all_available = new_available
    
    duration = timedelta(minutes=duration_minutes)
    valid_slots: list[dict[str, Any]] = []
    
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
    attendees: list[str],
    location: Optional[str] = None,
    description: Optional[str] = None,
    send_invites: bool = True,
    created_by: Optional[int] = None,
) -> dict[str, Any]:
    """Create a calendar event."""
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
