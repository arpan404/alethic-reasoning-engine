"""Calendar integration tools for Alethic agents.

These tools handle calendar API integrations for scheduling
and availability management.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

from sqlalchemy import select, and_

from database.engine import AsyncSessionLocal
from database.models.calendar import CalendarIntegration, CalendarEvent

logger = logging.getLogger(__name__)


async def find_available_time_slots(
    interviewer_ids: List[int],
    candidate_availability: Optional[List[Dict[str, datetime]]] = None,
    duration_minutes: int = 60,
    buffer_minutes: int = 15,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    working_hours_start: int = 9,
    working_hours_end: int = 17,
    timezone: str = "UTC",
) -> Dict[str, Any]:
    """Find available time slots for interviews.
    
    Queries connected calendars to find overlapping availability
    between interviewers and optionally the candidate.
    
    Args:
        interviewer_ids: User IDs of interviewers
        candidate_availability: Optional candidate available slots
        duration_minutes: Required duration in minutes
        buffer_minutes: Buffer time between meetings
        start_date: Search start date (defaults to tomorrow)
        end_date: Search end date (defaults to 2 weeks out)
        working_hours_start: Working day start hour (24h format)
        working_hours_end: Working day end hour (24h format)
        timezone: Timezone for working hours
        
    Returns:
        Dictionary with available time slots
    """
    if not interviewer_ids:
        return {
            "success": False,
            "error": "At least one interviewer is required",
        }
    
    if start_date is None:
        start_date = datetime.utcnow() + timedelta(days=1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if end_date is None:
        end_date = start_date + timedelta(days=14)
    
    async with AsyncSessionLocal() as session:
        # Get calendar events for all interviewers
        events_query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id.in_(interviewer_ids),
                CalendarEvent.start_time >= start_date,
                CalendarEvent.end_time <= end_date,
                CalendarEvent.status != "cancelled",
            )
        )
        result = await session.execute(events_query)
        existing_events = result.scalars().all()
        
        # Build busy times per interviewer
        busy_times = {uid: [] for uid in interviewer_ids}
        for event in existing_events:
            if event.user_id in busy_times:
                busy_times[event.user_id].append({
                    "start": event.start_time,
                    "end": event.end_time,
                })
    
    # Find available slots
    available_slots = []
    current_date = start_date.date()
    total_duration = duration_minutes + buffer_minutes
    
    while current_date <= end_date.date():
        # Skip weekends
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue
        
        # Check each 30-minute slot during working hours
        slot_time = datetime.combine(current_date, datetime.min.time())
        slot_time = slot_time.replace(hour=working_hours_start)
        day_end = slot_time.replace(hour=working_hours_end)
        
        while slot_time + timedelta(minutes=total_duration) <= day_end:
            slot_end = slot_time + timedelta(minutes=duration_minutes)
            
            # Check if all interviewers are available
            all_available = True
            for uid in interviewer_ids:
                for busy in busy_times.get(uid, []):
                    # Check for overlap
                    if not (slot_end <= busy["start"] or slot_time >= busy["end"]):
                        all_available = False
                        break
                if not all_available:
                    break
            
            # Check candidate availability if provided
            if all_available and candidate_availability:
                candidate_available = False
                for slot in candidate_availability:
                    if slot["start"] <= slot_time and slot["end"] >= slot_end:
                        candidate_available = True
                        break
                all_available = candidate_available
            
            if all_available:
                available_slots.append({
                    "start": slot_time.isoformat(),
                    "end": slot_end.isoformat(),
                    "duration_minutes": duration_minutes,
                })
            
            slot_time += timedelta(minutes=30)
        
        current_date += timedelta(days=1)
    
    return {
        "success": True,
        "interviewer_ids": interviewer_ids,
        "search_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "working_hours": f"{working_hours_start}:00 - {working_hours_end}:00",
        "duration_minutes": duration_minutes,
        "available_slots": available_slots[:50],  # Limit to 50 slots
        "total_slots_found": len(available_slots),
    }


async def create_calendar_event(
    user_id: int,
    title: str,
    start_time: datetime,
    end_time: datetime,
    attendees: Optional[List[str]] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    meeting_link: Optional[str] = None,
    send_invites: bool = True,
) -> Dict[str, Any]:
    """Create a calendar event via connected calendar integration.
    
    Args:
        user_id: User ID (calendar owner)
        title: Event title
        start_time: Event start time
        end_time: Event end time
        attendees: List of attendee email addresses
        description: Event description
        location: Physical location
        meeting_link: Video meeting link
        send_invites: Whether to send calendar invites
        
    Returns:
        Dictionary with created event details
    """
    async with AsyncSessionLocal() as session:
        # Check for calendar integration
        integration_query = select(CalendarIntegration).where(
            and_(
                CalendarIntegration.user_id == user_id,
                CalendarIntegration.is_active == True,
            )
        )
        result = await session.execute(integration_query)
        integration = result.scalar_one_or_none()
        
        if not integration:
            return {
                "success": False,
                "error": "No active calendar integration found for user",
            }
        
        # Create event record
        event = CalendarEvent(
            user_id=user_id,
            integration_id=integration.id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            meeting_link=meeting_link,
            attendees=attendees or [],
            status="confirmed",
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
    
    # Queue the external calendar sync
    from agents.tools.queue import enqueue_task
    await enqueue_task(
        task_type="sync_calendar_event",
        payload={
            "event_id": event.id,
            "action": "create",
            "send_invites": send_invites,
        },
        priority="high",
    )
    
    logger.info(f"Created calendar event {event.id}: {title}")
    
    return {
        "success": True,
        "event_id": event.id,
        "title": title,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "attendees": attendees or [],
        "invites_queued": send_invites,
    }


async def get_calendar_availability(
    user_id: int,
    start_date: datetime,
    end_date: datetime,
) -> Dict[str, Any]:
    """Get calendar availability for a user.
    
    Args:
        user_id: User ID to check
        start_date: Start of period
        end_date: End of period
        
    Returns:
        Dictionary with availability data
    """
    async with AsyncSessionLocal() as session:
        events_query = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= start_date,
                CalendarEvent.end_time <= end_date,
                CalendarEvent.status != "cancelled",
            )
        ).order_by(CalendarEvent.start_time)
        
        result = await session.execute(events_query)
        events = result.scalars().all()
    
    busy_times = []
    for event in events:
        busy_times.append({
            "start": event.start_time.isoformat(),
            "end": event.end_time.isoformat(),
            "title": event.title,
            "is_all_day": event.is_all_day,
        })
    
    return {
        "user_id": user_id,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "busy_times": busy_times,
        "event_count": len(events),
    }
