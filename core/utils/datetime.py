"""Datetime utilities for common operations."""

from datetime import datetime, date, time, timedelta, timezone
from typing import Optional
import re


def now() -> datetime:
    """Get current datetime in UTC."""
    return datetime.now(timezone.utc)


def today() -> date:
    """Get current date in UTC."""
    return datetime.now(timezone.utc).date()


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string in various formats.
    
    Args:
        date_str: Date string to parse
        
    Returns:
        Parsed date or None if invalid
    """
    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None


def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parse datetime string in various formats.
    
    Args:
        datetime_str: Datetime string to parse
        
    Returns:
        Parsed datetime or None if invalid
    """
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
        "%m/%d/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            # Make timezone aware if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    return None


def add_days(dt: datetime | date, days: int) -> datetime | date:
    """
    Add days to a date or datetime.
    
    Args:
        dt: Date or datetime
        days: Number of days to add (can be negative)
        
    Returns:
        New date or datetime
    """
    if isinstance(dt, datetime):
        return dt + timedelta(days=days)
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """
    Add hours to a datetime.
    
    Args:
        dt: Datetime
        hours: Number of hours to add (can be negative)
        
    Returns:
        New datetime
    """
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """
    Add minutes to a datetime.
    
    Args:
        dt: Datetime
        minutes: Number of minutes to add (can be negative)
        
    Returns:
        New datetime
    """
    return dt + timedelta(minutes=minutes)


def start_of_day(dt: datetime | date) -> datetime:
    """
    Get start of day (00:00:00).
    
    Args:
        dt: Date or datetime
        
    Returns:
        Datetime at start of day
    """
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, time.min)
    
    return dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def end_of_day(dt: datetime | date) -> datetime:
    """
    Get end of day (23:59:59.999999).
    
    Args:
        dt: Date or datetime
        
    Returns:
        Datetime at end of day
    """
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, time.max)
    
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)


def days_between(start: datetime | date, end: datetime | date) -> int:
    """
    Calculate number of days between two dates.
    
    Args:
        start: Start date
        end: End date
        
    Returns:
        Number of days
    """
    if isinstance(start, datetime):
        start = start.date()
    if isinstance(end, datetime):
        end = end.date()
    
    return (end - start).days


def hours_between(start: datetime, end: datetime) -> float:
    """
    Calculate number of hours between two datetimes.
    
    Args:
        start: Start datetime
        end: End datetime
        
    Returns:
        Number of hours (can be fractional)
    """
    delta = end - start
    return delta.total_seconds() / 3600


def is_past(dt: datetime | date) -> bool:
    """
    Check if date/datetime is in the past.
    
    Args:
        dt: Date or datetime to check
        
    Returns:
        True if in the past
    """
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt < today()
    
    return dt < now()


def is_future(dt: datetime | date) -> bool:
    """
    Check if date/datetime is in the future.
    
    Args:
        dt: Date or datetime to check
        
    Returns:
        True if in the future
    """
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt > today()
    
    return dt > now()


def is_within_days(dt: datetime | date, days: int) -> bool:
    """
    Check if date is within specified number of days from now.
    
    Args:
        dt: Date or datetime to check
        days: Number of days
        
    Returns:
        True if within days
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    diff = abs((dt - today()).days)
    return diff <= days


def format_relative(dt: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 hours ago").
    
    Args:
        dt: Datetime to format
        
    Returns:
        Relative time string
    """
    diff = now() - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


def get_weekday_name(dt: datetime | date) -> str:
    """
    Get weekday name from date.
    
    Args:
        dt: Date or datetime
        
    Returns:
        Weekday name (e.g., "Monday")
    """
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return weekdays[dt.weekday()]


def is_weekend(dt: datetime | date) -> bool:
    """
    Check if date falls on weekend.
    
    Args:
        dt: Date or datetime to check
        
    Returns:
        True if weekend
    """
    return dt.weekday() >= 5


def is_business_day(dt: datetime | date) -> bool:
    """
    Check if date is a business day (weekday).
    
    Args:
        dt: Date or datetime to check
        
    Returns:
        True if business day
    """
    return not is_weekend(dt)


def next_business_day(dt: datetime | date) -> date:
    """
    Get next business day from given date.
    
    Args:
        dt: Starting date
        
    Returns:
        Next business day
    """
    if isinstance(dt, datetime):
        dt = dt.date()
    
    next_day = dt + timedelta(days=1)
    
    while is_weekend(next_day):
        next_day += timedelta(days=1)
    
    return next_day


def to_unix_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Unix timestamp (seconds since epoch)
    """
    return int(dt.timestamp())


def from_unix_timestamp(timestamp: int) -> datetime:
    """
    Convert Unix timestamp to datetime.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Datetime in UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
