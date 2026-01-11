"""Shared tools available to all agents."""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text.
    
    Args:
        text: Text to search for email
        
    Returns:
        Email address if found, None otherwise
    """
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from text.
    
    Args:
        text: Text to search for phone number
        
    Returns:
        Phone number if found, None otherwise
    """
    # Match various phone formats
    patterns = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text.
    
    Args:
        text: Text to search for URLs
        
    Returns:
        List of URLs found
    """
    pattern = r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    return re.findall(pattern, text)


def extract_linkedin_url(text: str) -> Optional[str]:
    """Extract LinkedIn profile URL from text.
    
    Args:
        text: Text to search for LinkedIn URL
        
    Returns:
        LinkedIn URL if found, None otherwise
    """
    pattern = r'https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_github_url(text: str) -> Optional[str]:
    """Extract GitHub profile URL from text.
    
    Args:
        text: Text to search for GitHub URL
        
    Returns:
        GitHub URL if found, None otherwise
    """
    pattern = r'https?://(?:www\.)?github\.com/[a-zA-Z0-9-]+'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse various date formats.
    
    Args:
        date_string: Date string to parse
        
    Returns:
        datetime object if successfully parsed, None otherwise
    """
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%B %Y',
        '%b %Y',
        '%Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    
    return None


def calculate_duration(start_date: datetime, end_date: Optional[datetime] = None) -> Dict[str, int]:
    """Calculate duration between dates.
    
    Args:
        start_date: Start date
        end_date: End date (defaults to now if None)
        
    Returns:
        Dictionary with years and months
    """
    if end_date is None:
        end_date = datetime.now()
    
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    years = months // 12
    remaining_months = months % 12
    
    return {
        "years": years,
        "months": remaining_months,
        "total_months": months,
    }


def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and special characters.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text.strip()


def extract_skills_keywords(text: str, skill_list: List[str]) -> List[str]:
    """Extract skills from text based on a known skill list.
    
    Args:
        text: Text to search for skills
        skill_list: List of known skills to search for
        
    Returns:
        List of found skills
    """
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_list:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    return list(set(found_skills))  # Remove duplicates


def score_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple similarity score between two texts.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    words1 = set(normalize_text(text1).lower().split())
    words2 = set(normalize_text(text2).lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0
