"""Calendar integration utilities (Google Calendar)."""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class CalendarEvent:
    """Represents a calendar event."""
    
    def __init__(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        event_id: Optional[str] = None,
    ):
        """
        Initialize calendar event.
        
        Args:
            title: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            location: Event location
            attendees: List of attendee emails
            event_id: Event ID (for existing events)
        """
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.description = description
        self.location = location
        self.attendees = attendees or []
        self.event_id = event_id
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary format."""
        return {
            'summary': self.title,
            'description': self.description,
            'location': self.location,
            'start': {
                'dateTime': self.start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': self.end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'attendees': [{'email': email} for email in self.attendees],
        }


class CalendarService:
    """Calendar service for managing calendar events (Google Calendar)."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize calendar service.
        
        Args:
            credentials_path: Path to Google Calendar API credentials
        """
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CALENDAR_CREDENTIALS")
        self._service = None
    
    def _get_service(self):
        """Get or create Google Calendar service instance."""
        if self._service is None:
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build
                
                if not self.credentials_path:
                    raise ValueError("Google Calendar credentials not configured")
                
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                
                self._service = build('calendar', 'v3', credentials=credentials)
                logger.info("Google Calendar service initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize Google Calendar service: {e}")
                raise
        
        return self._service
    
    def create_event(
        self,
        event: CalendarEvent,
        calendar_id: str = 'primary',
        send_notifications: bool = True
    ) -> Optional[str]:
        """
        Create a calendar event.
        
        Args:
            event: Calendar event to create
            calendar_id: Calendar ID (default: primary)
            send_notifications: Whether to send email notifications
            
        Returns:
            Event ID if successful, None otherwise
        """
        try:
            service = self._get_service()
            
            event_data = event.to_dict()
            created_event = service.events().insert(
                calendarId=calendar_id,
                body=event_data,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()
            
            event_id = created_event.get('id')
            logger.info(f"Created calendar event: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None
    
    def update_event(
        self,
        event: CalendarEvent,
        calendar_id: str = 'primary',
        send_notifications: bool = True
    ) -> bool:
        """
        Update an existing calendar event.
        
        Args:
            event: Calendar event with updated data (must have event_id)
            calendar_id: Calendar ID (default: primary)
            send_notifications: Whether to send email notifications
            
        Returns:
            True if successful
        """
        if not event.event_id:
            logger.error("Event ID required for update")
            return False
        
        try:
            service = self._get_service()
            
            event_data = event.to_dict()
            service.events().update(
                calendarId=calendar_id,
                eventId=event.event_id,
                body=event_data,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()
            
            logger.info(f"Updated calendar event: {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return False
    
    def delete_event(
        self,
        event_id: str,
        calendar_id: str = 'primary',
        send_notifications: bool = True
    ) -> bool:
        """
        Delete a calendar event.
        
        Args:
            event_id: Event ID to delete
            calendar_id: Calendar ID (default: primary)
            send_notifications: Whether to send email notifications
            
        Returns:
            True if successful
        """
        try:
            service = self._get_service()
            
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendUpdates='all' if send_notifications else 'none'
            ).execute()
            
            logger.info(f"Deleted calendar event: {event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False
    
    def get_event(
        self,
        event_id: str,
        calendar_id: str = 'primary'
    ) -> Optional[CalendarEvent]:
        """
        Get a calendar event by ID.
        
        Args:
            event_id: Event ID
            calendar_id: Calendar ID (default: primary)
            
        Returns:
            CalendarEvent if found, None otherwise
        """
        try:
            service = self._get_service()
            
            event_data = service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return self._parse_event(event_data)
            
        except Exception as e:
            logger.error(f"Failed to get calendar event: {e}")
            return None
    
    def list_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        calendar_id: str = 'primary',
        max_results: int = 10
    ) -> List[CalendarEvent]:
        """
        List calendar events in a time range.
        
        Args:
            start_time: Start of time range (default: now)
            end_time: End of time range (default: 30 days from now)
            calendar_id: Calendar ID (default: primary)
            max_results: Maximum number of events to return
            
        Returns:
            List of CalendarEvent objects
        """
        if start_time is None:
            start_time = datetime.utcnow()
        
        if end_time is None:
            end_time = start_time + timedelta(days=30)
        
        try:
            service = self._get_service()
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [self._parse_event(event_data) for event_data in events]
            
        except Exception as e:
            logger.error(f"Failed to list calendar events: {e}")
            return []
    
    def find_available_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int = 60,
        calendar_id: str = 'primary'
    ) -> List[tuple[datetime, datetime]]:
        """
        Find available time slots in calendar.
        
        Args:
            start_date: Start of search range
            end_date: End of search range
            duration_minutes: Desired meeting duration in minutes
            calendar_id: Calendar ID (default: primary)
            
        Returns:
            List of (start_time, end_time) tuples for available slots
        """
        # Get existing events
        events = self.list_events(start_date, end_date, calendar_id, max_results=100)
        
        # Find gaps between events
        available_slots = []
        current_time = start_date
        
        for event in sorted(events, key=lambda e: e.start_time):
            # Check if there's a gap before this event
            if event.start_time > current_time + timedelta(minutes=duration_minutes):
                available_slots.append((current_time, event.start_time))
            
            # Move to end of this event
            if event.end_time > current_time:
                current_time = event.end_time
        
        # Check if there's time after the last event
        if end_date > current_time + timedelta(minutes=duration_minutes):
            available_slots.append((current_time, end_date))
        
        return available_slots
    
    def _parse_event(self, event_data: Dict) -> CalendarEvent:
        """Parse event data from Google Calendar API."""
        return CalendarEvent(
            title=event_data.get('summary', ''),
            start_time=datetime.fromisoformat(
                event_data['start'].get('dateTime', event_data['start'].get('date'))
            ),
            end_time=datetime.fromisoformat(
                event_data['end'].get('dateTime', event_data['end'].get('date'))
            ),
            description=event_data.get('description'),
            location=event_data.get('location'),
            attendees=[
                attendee['email']
                for attendee in event_data.get('attendees', [])
            ],
            event_id=event_data.get('id')
        )


# Global calendar service instance
_calendar_service: Optional[CalendarService] = None


def get_calendar_service() -> CalendarService:
    """Get or create global calendar service instance."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService()
    return _calendar_service
