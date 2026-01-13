"""Formatting utilities for common data types."""

from typing import Optional
from datetime import datetime, date
import re


def format_name(first_name: Optional[str], last_name: Optional[str]) -> str:
    """
    Format full name from first and last names.
    
    Args:
        first_name: First name
        last_name: Last name
        
    Returns:
        Formatted full name
    """
    parts = []
    if first_name:
        parts.append(first_name.strip())
    if last_name:
        parts.append(last_name.strip())
    return ' '.join(parts)


def format_phone(phone: str) -> str:
    """
    Format phone number for display (US format).
    
    Args:
        phone: Phone number to format
        
    Returns:
        Formatted phone number
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Amount to format
        currency: Currency code (default: USD)
        
    Returns:
        Formatted currency string
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CAD": "C$",
        "AUD": "A$",
    }
    
    symbol = symbols.get(currency, currency + " ")
    
    # Format with thousands separator
    if currency == "JPY":
        # No decimal places for JPY
        return f"{symbol}{int(amount):,}"
    else:
        return f"{symbol}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage for display.
    
    Args:
        value: Percentage value (0-100)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"


def format_date(dt: datetime | date, format_str: str = "%Y-%m-%d") -> str:
    """
    Format date for display.
    
    Args:
        dt: Date or datetime to format
        format_str: Format string
        
    Returns:
        Formatted date string
    """
    return dt.strftime(format_str)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime to format
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted file size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """
    Convert text to URL-safe slug.
    
    Args:
        text: Text to convert
        
    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    
    # Remove consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    return text


def format_initials(first_name: str, last_name: str) -> str:
    """
    Generate initials from first and last names.
    
    Args:
        first_name: First name
        last_name: Last name
        
    Returns:
        Initials (e.g., "JD")
    """
    initials = ""
    if first_name:
        initials += first_name[0].upper()
    if last_name:
        initials += last_name[0].upper()
    return initials


def format_list(items: list[str], conjunction: str = "and") -> str:
    """
    Format list of items into readable string.
    
    Args:
        items: List of items
        conjunction: Conjunction to use (and/or)
        
    Returns:
        Formatted string (e.g., "A, B, and C")
    """
    if not items:
        return ""
    
    if len(items) == 1:
        return items[0]
    
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    
    return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Args:
        email: Email address to mask
        
    Returns:
        Masked email (e.g., "j***@example.com")
    """
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number for privacy.
    
    Args:
        phone: Phone number to mask
        
    Returns:
        Masked phone (e.g., "***-***-1234")
    """
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) >= 4:
        return '*' * (len(digits) - 4) + digits[-4:]
    
    return phone
