"""Shared utility functions for agents."""

import json
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON from agent response.
    
    Args:
        response: Agent response text that may contain JSON
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    # Try to extract JSON from markdown code blocks
    if "```json" in response:
        try:
            start = response.find("```json") + 7
            end = response.find("```", start)
            json_str = response[start:end].strip()
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to parse JSON from code block: {e}")
    
    # Try to parse the entire response
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        logger.warning("Response is not valid JSON")
        return None


def format_agent_context(context: Dict[str, Any]) -> str:
    """Format context dictionary for agent consumption.
    
    Args:
        context: Context data to format
        
    Returns:
        Formatted context string
    """
    lines = []
    for key, value in context.items():
        if isinstance(value, (list, dict)):
            lines.append(f"{key.replace('_', ' ').title()}:")
            lines.append(json.dumps(value, indent=2))
        else:
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
    
    return "\n".join(lines)


def validate_agent_output(
    output: Dict[str, Any],
    required_fields: List[str],
) -> tuple[bool, Optional[str]]:
    """Validate agent output has required fields.
    
    Args:
        output: Agent output to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in output:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def chunk_text(text: str, max_length: int = 2000, overlap: int = 200) -> List[str]:
    """Split text into chunks for processing.
    
    Args:
        text: Text to chunk
        max_length: Maximum chunk length
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_length
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence ending punctuation
            for punct in ['. ', '! ', '? ', '\n\n']:
                last_punct = text.rfind(punct, start, end)
                if last_punct > start:
                    end = last_punct + len(punct)
                    break
        
        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else end
    
    return chunks


def merge_agent_results(results: List[Dict[str, Any]], strategy: str = "latest") -> Dict[str, Any]:
    """Merge multiple agent results.
    
    Args:
        results: List of result dictionaries
        strategy: Merge strategy ("latest", "highest_confidence", "combine")
        
    Returns:
        Merged result dictionary
    """
    if not results:
        return {}
    
    if len(results) == 1:
        return results[0]
    
    if strategy == "latest":
        return results[-1]
    
    elif strategy == "highest_confidence":
        # Assumes results have a 'confidence' field
        return max(results, key=lambda x: x.get("confidence", 0))
    
    elif strategy == "combine":
        # Combine all results, later ones override earlier ones
        merged = {}
        for result in results:
            merged.update(result)
        return merged
    
    return results[-1]


def sanitize_for_logging(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """Remove sensitive information from data for logging.
    
    Args:
        data: Data to sanitize
        sensitive_keys: List of keys to redact
        
    Returns:
        Sanitized data dictionary
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "password", "token", "secret", "api_key", "private_key",
            "credit_card", "ssn", "social_security",
        ]
    
    sanitized = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if key contains sensitive terms
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_for_logging(value, sensitive_keys)
        else:
            sanitized[key] = value
    
    return sanitized


def calculate_confidence_score(scores: Dict[str, float], weights: Dict[str, float] = None) -> float:
    """Calculate weighted confidence score.
    
    Args:
        scores: Dictionary of component scores (0-1)
        weights: Dictionary of weights for each score (defaults to equal weights)
        
    Returns:
        Overall confidence score (0-1)
    """
    if not scores:
        return 0.0
    
    if weights is None:
        weights = {key: 1.0 for key in scores.keys()}
    
    total_weight = sum(weights.get(key, 1.0) for key in scores.keys())
    weighted_sum = sum(score * weights.get(key, 1.0) for key, score in scores.items())
    
    return weighted_sum / total_weight if total_weight > 0 else 0.0
