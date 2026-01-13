"""Validation utilities for common data types."""

import re
from typing import Optional
from email_validator import validate_email as _validate_email, EmailNotValidError


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, normalized_email or error_message)
    """
    try:
        validation = _validate_email(email, check_deliverability=False)
        return True, validation.normalized
    except EmailNotValidError as e:
        return False, str(e)


def validate_phone(phone: str) -> tuple[bool, Optional[str]]:
    """
    Validate phone number format (basic validation).
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
    
    # Check if it contains at least some digits
    if not re.search(r'\d', cleaned):
        return False, "Phone number must contain digits"
    
    # Check if it's a reasonable length (7-15 digits)
    digits = re.findall(r'\d', cleaned)
    if len(digits) < 7 or len(digits) > 15:
        return False, "Phone number must be between 7 and 15 digits"
    
    return True, None


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    # Basic URL pattern
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    return True, None


def validate_linkedin_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate LinkedIn profile URL.
    
    Args:
        url: LinkedIn URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return True, None  # Optional field
    
    linkedin_pattern = re.compile(
        r'^https?://(www\.)?linkedin\.com/(in|pub)/[a-zA-Z0-9_-]+/?$',
        re.IGNORECASE
    )
    
    if not linkedin_pattern.match(url):
        return False, "Invalid LinkedIn URL format"
    
    return True, None


def validate_github_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate GitHub profile URL.
    
    Args:
        url: GitHub URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return True, None  # Optional field
    
    github_pattern = re.compile(
        r'^https?://(www\.)?github\.com/[a-zA-Z0-9_-]+/?$',
        re.IGNORECASE
    )
    
    if not github_pattern.match(url):
        return False, "Invalid GitHub URL format"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and other dangerous chars
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        sanitized = name[:250] + ('.' + ext if ext else '')
    
    return sanitized


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if len(password) > 128:
        errors.append("Password must be less than 128 characters")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


def validate_slug(slug: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL slug format.
    
    Args:
        slug: Slug to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not slug:
        return False, "Slug is required"
    
    # Only lowercase letters, numbers, and hyphens
    if not re.match(r'^[a-z0-9-]+$', slug):
        return False, "Slug can only contain lowercase letters, numbers, and hyphens"
    
    # Can't start or end with hyphen
    if slug.startswith('-') or slug.endswith('-'):
        return False, "Slug cannot start or end with a hyphen"
    
    # No consecutive hyphens
    if '--' in slug:
        return False, "Slug cannot contain consecutive hyphens"
    
    return True, None


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to E.164 format (basic version).
    
    Args:
        phone: Phone number to normalize
        
    Returns:
        Normalized phone number
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # If no +, assume US number and add +1
    if not cleaned.startswith('+'):
        cleaned = '+1' + cleaned
    
    return cleaned
