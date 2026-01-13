"""Extended shared tools for agents."""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


def fuzzy_match(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """Check if two texts match with fuzzy matching.
    
    Args:
        text1: First text
        text2: Second text
        threshold: Similarity threshold (0-1)
        
    Returns:
        True if texts match above threshold
    """
    ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    return ratio >= threshold


def extract_names(text: str) -> List[str]:
    """Extract potential names from text using simple patterns.
    
    Args:
        text: Text to search for names
        
    Returns:
        List of potential names
    """
    # Match capitalized words (simple name pattern)
    pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
    return re.findall(pattern, text)


def extract_companies(text: str, company_keywords: Optional[List[str]] = None) -> List[str]:
    """Extract company names from text.
    
    Args:
        text: Text to search for companies
        company_keywords: Optional list of known company keywords
        
    Returns:
        List of potential company names
    """
    # Common company suffixes
    suffixes = ['Inc', 'LLC', 'Corp', 'Corporation', 'Ltd', 'Limited', 'Company', 'Co']
    pattern = r'\b[A-Z][A-Za-z\s&]+(?:' + '|'.join(suffixes) + r')\.?\b'
    companies = re.findall(pattern, text)
    
    # Also check against known companies
    if company_keywords:
        text_lower = text.lower()
        for company in company_keywords:
            if company.lower() in text_lower:
                companies.append(company)
    
    return list(set(companies))


def extract_years_of_experience(text: str) -> Optional[float]:
    """Extract years of experience from text.
    
    Args:
        text: Text to search
        
    Returns:
        Years of experience as float, None if not found
    """
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*(?:of\s*)?experience',
        r'experience\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:years?|yrs?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None


def extract_salary(text: str) -> Optional[Dict[str, Any]]:
    """Extract salary information from text.
    
    Args:
        text: Text to search
        
    Returns:
        Dictionary with salary info or None
    """
    # Match patterns like $50,000, $50K, $50k-$60k, etc.
    pattern = r'\$(\d+(?:,\d{3})*(?:k|K)?)\s*(?:-\s*\$?(\d+(?:,\d{3})*(?:k|K)?))?'
    match = re.search(pattern, text)
    
    if not match:
        return None
    
    def parse_amount(amount_str: str) -> int:
        # Remove commas
        amount_str = amount_str.replace(',', '')
        # Handle K suffix
        if amount_str.lower().endswith('k'):
            return int(float(amount_str[:-1]) * 1000)
        return int(amount_str)
    
    result = {"min": parse_amount(match.group(1))}
    
    if match.group(2):
        result["max"] = parse_amount(match.group(2))
    else:
        result["max"] = result["min"]
    
    return result


def extract_degree(text: str) -> List[str]:
    """Extract educational degrees from text.
    
    Args:
        text: Text to search
        
    Returns:
        List of degrees found
    """
    degrees = [
        r'\b(?:PhD|Ph\.D\.|Doctor of Philosophy)\b',
        r'\b(?:Master|M\.S\.|M\.A\.|MBA|M\.B\.A\.)\b',
        r'\b(?:Bachelor|B\.S\.|B\.A\.|B\.Sc\.|B\.Tech)\b',
        r'\b(?:Associate|A\.S\.|A\.A\.)\b',
    ]
    
    found_degrees = []
    for degree_pattern in degrees:
        matches = re.findall(degree_pattern, text, re.IGNORECASE)
        found_degrees.extend(matches)
    
    return list(set(found_degrees))


def clean_text(text: str) -> str:
    """Clean text by removing unwanted characters and normalizing.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove emails
    text = re.sub(r'\S+@\S+', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters except punctuation
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    return text.strip()


def format_bullet_points(items: List[str]) -> str:
    """Format list items as bullet points.
    
    Args:
        items: List of items to format
        
    Returns:
        Formatted bullet point string
    """
    return '\n'.join(f'• {item}' for item in items)


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentences
    """
    # Simple sentence splitter
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def extract_section(text: str, section_headers: List[str]) -> Optional[str]:
    """Extract a section from text based on headers.
    
    Args:
        text: Text to search
        section_headers: Possible section header names
        
    Returns:
        Section text if found, None otherwise
    """
    for header in section_headers:
        # Case insensitive search for section header
        pattern = rf'{re.escape(header)}\s*:?\s*(.*?)(?=\n[A-Z][a-z]+:|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return None


def calculate_word_count(text: str) -> int:
    """Calculate word count in text.
    
    Args:
        text: Text to count words in
        
    Returns:
        Number of words
    """
    return len(text.split())


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length.
    
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


def highlight_keywords(text: str, keywords: List[str], marker: str = "**") -> str:
    """Highlight keywords in text.
    
    Args:
        text: Text to process
        keywords: Keywords to highlight
        marker: Marker to use for highlighting (default: markdown bold)
        
    Returns:
        Text with highlighted keywords
    """
    for keyword in keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        text = pattern.sub(f'{marker}{keyword}{marker}', text)
    
    return text
