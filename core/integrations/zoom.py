"""Zoom integration utilities for video conferencing."""

import os
import jwt
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import httpx
import logging

logger = logging.getLogger(__name__)


class ZoomMeeting:
    """Represents a Zoom meeting."""
    
    def __init__(
        self,
        topic: str,
        start_time: datetime,
        duration_minutes: int,
        meeting_id: Optional[str] = None,
        join_url: Optional[str] = None,
        password: Optional[str] = None,
        agenda: Optional[str] = None,
    ):
        """
        Initialize Zoom meeting.
        
        Args:
            topic: Meeting topic
            start_time: Meeting start time
            duration_minutes: Meeting duration in minutes
            meeting_id: Zoom meeting ID
            join_url: Meeting join URL
            password: Meeting password
            agenda: Meeting agenda
        """
        self.topic = topic
        self.start_time = start_time
        self.duration_minutes = duration_minutes
        self.meeting_id = meeting_id
        self.join_url = join_url
        self.password = password
        self.agenda = agenda
    
    def to_dict(self) -> Dict:
        """Convert meeting to dictionary format."""
        return {
            'topic': self.topic,
            'type': 2,  # Scheduled meeting
            'start_time': self.start_time.isoformat(),
            'duration': self.duration_minutes,
            'timezone': 'UTC',
            'agenda': self.agenda,
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'waiting_room': True,
                'audio': 'both',
            }
        }


class ZoomService:
    """Zoom service for managing video meetings."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Initialize Zoom service.
        
        Args:
            api_key: Zoom API key (JWT)
            api_secret: Zoom API secret (JWT)
            account_id: Zoom account ID (OAuth)
            client_id: Zoom client ID (OAuth)
            client_secret: Zoom client secret (OAuth)
        """
        # JWT Auth (deprecated but simpler)
        self.api_key = api_key or os.getenv("ZOOM_API_KEY")
        self.api_secret = api_secret or os.getenv("ZOOM_API_SECRET")
        
        # OAuth Auth (recommended)
        self.account_id = account_id or os.getenv("ZOOM_ACCOUNT_ID")
        self.client_id = client_id or os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ZOOM_CLIENT_SECRET")
        
        self.base_url = "https://api.zoom.us/v2"
        self._access_token = None
        self._token_expiry = None
    
    def _generate_jwt_token(self) -> str:
        """Generate JWT token for Zoom API (legacy method)."""
        if not self.api_key or not self.api_secret:
            raise ValueError("Zoom API key and secret required for JWT auth")
        
        token = jwt.encode(
            {
                'iss': self.api_key,
                'exp': int(time.time()) + 3600,
            },
            self.api_secret,
            algorithm='HS256'
        )
        
        return token
    
    async def _get_oauth_token(self) -> str:
        """Get OAuth access token."""
        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._access_token
        
        if not all([self.account_id, self.client_id, self.client_secret]):
            raise ValueError("Zoom OAuth credentials required")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://zoom.us/oauth/token",
                params={
                    'grant_type': 'account_credentials',
                    'account_id': self.account_id,
                },
                auth=(self.client_id, self.client_secret)
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get OAuth token: {response.text}")
            
            data = response.json()
            self._access_token = data['access_token']
            self._token_expiry = datetime.now() + timedelta(seconds=data['expires_in'] - 300)
            
            return self._access_token
    
    async def _get_headers(self) -> Dict:
        """Get API request headers with authentication."""
        if self.client_id and self.client_secret:
            # Use OAuth
            token = await self._get_oauth_token()
        else:
            # Use JWT (legacy)
            token = self._generate_jwt_token()
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
    
    async def create_meeting(
        self,
        meeting: ZoomMeeting,
        user_id: str = 'me'
    ) -> Optional[ZoomMeeting]:
        """
        Create a Zoom meeting.
        
        Args:
            meeting: Zoom meeting to create
            user_id: Zoom user ID (default: 'me' for API user)
            
        Returns:
            Created meeting with meeting_id and join_url
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/users/{user_id}/meetings",
                    headers=headers,
                    json=meeting.to_dict()
                )
                
                if response.status_code != 201:
                    logger.error(f"Failed to create Zoom meeting: {response.text}")
                    return None
                
                data = response.json()
                
                meeting.meeting_id = str(data['id'])
                meeting.join_url = data['join_url']
                meeting.password = data.get('password')
                
                logger.info(f"Created Zoom meeting: {meeting.meeting_id}")
                return meeting
                
        except Exception as e:
            logger.error(f"Failed to create Zoom meeting: {e}")
            return None
    
    async def get_meeting(
        self,
        meeting_id: str
    ) -> Optional[ZoomMeeting]:
        """
        Get a Zoom meeting by ID.
        
        Args:
            meeting_id: Meeting ID
            
        Returns:
            ZoomMeeting if found
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/meetings/{meeting_id}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get Zoom meeting: {response.text}")
                    return None
                
                data = response.json()
                return self._parse_meeting(data)
                
        except Exception as e:
            logger.error(f"Failed to get Zoom meeting: {e}")
            return None
    
    async def update_meeting(
        self,
        meeting: ZoomMeeting
    ) -> bool:
        """
        Update a Zoom meeting.
        
        Args:
            meeting: Meeting with updated data (must have meeting_id)
            
        Returns:
            True if successful
        """
        if not meeting.meeting_id:
            logger.error("Meeting ID required for update")
            return False
        
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/meetings/{meeting.meeting_id}",
                    headers=headers,
                    json=meeting.to_dict()
                )
                
                if response.status_code != 204:
                    logger.error(f"Failed to update Zoom meeting: {response.text}")
                    return False
                
                logger.info(f"Updated Zoom meeting: {meeting.meeting_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update Zoom meeting: {e}")
            return False
    
    async def delete_meeting(
        self,
        meeting_id: str
    ) -> bool:
        """
        Delete a Zoom meeting.
        
        Args:
            meeting_id: Meeting ID to delete
            
        Returns:
            True if successful
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/meetings/{meeting_id}",
                    headers=headers
                )
                
                if response.status_code != 204:
                    logger.error(f"Failed to delete Zoom meeting: {response.text}")
                    return False
                
                logger.info(f"Deleted Zoom meeting: {meeting_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete Zoom meeting: {e}")
            return False
    
    async def list_meetings(
        self,
        user_id: str = 'me',
        meeting_type: str = 'scheduled'
    ) -> List[ZoomMeeting]:
        """
        List Zoom meetings for a user.
        
        Args:
            user_id: Zoom user ID (default: 'me')
            meeting_type: Type of meetings (scheduled, live, upcoming)
            
        Returns:
            List of ZoomMeeting objects
        """
        try:
            headers = await self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/{user_id}/meetings",
                    headers=headers,
                    params={'type': meeting_type}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to list Zoom meetings: {response.text}")
                    return []
                
                data = response.json()
                return [
                    self._parse_meeting(meeting_data)
                    for meeting_data in data.get('meetings', [])
                ]
                
        except Exception as e:
            logger.error(f"Failed to list Zoom meetings: {e}")
            return []
    
    def _parse_meeting(self, data: Dict) -> ZoomMeeting:
        """Parse meeting data from Zoom API."""
        return ZoomMeeting(
            topic=data.get('topic', ''),
            start_time=datetime.fromisoformat(data['start_time'].replace('Z', '+00:00')),
            duration_minutes=data.get('duration', 60),
            meeting_id=str(data.get('id', '')),
            join_url=data.get('join_url'),
            password=data.get('password'),
            agenda=data.get('agenda')
        )


# Global Zoom service instance
_zoom_service: Optional[ZoomService] = None


def get_zoom_service() -> ZoomService:
    """Get or create global Zoom service instance."""
    global _zoom_service
    if _zoom_service is None:
        _zoom_service = ZoomService()
    return _zoom_service
