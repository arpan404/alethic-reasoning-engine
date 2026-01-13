"""Shared utility functions for agents."""

import asyncio
import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


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


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """Decorator to retry async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
            
            raise last_exception
        
        return wrapper
    return decorator


def merge_agent_outputs(outputs: List[Dict[str, Any]], strategy: str = "merge") -> Dict[str, Any]:
    """Merge multiple agent outputs.
    
    Args:
        outputs: List of agent outputs
        strategy: Merge strategy ("merge", "first", "last")
        
    Returns:
        Merged output
    """
    if not outputs:
        return {}
    
    if strategy == "first":
        return outputs[0]
    elif strategy == "last":
        return outputs[-1]
    elif strategy == "merge":
        merged = {}
        for output in outputs:
            for key, value in output.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, list) and isinstance(merged[key], list):
                    merged[key].extend(value)
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    merged[key].update(value)
                else:
                    merged[key] = value
        return merged
    else:
        raise ValueError(f"Unknown merge strategy: {strategy}")


def rank_results(
    items: List[Dict[str, Any]],
    score_field: str = "score",
    reverse: bool = True
) -> List[Dict[str, Any]]:
    """Rank results by score.
    
    Args:
        items: List of items to rank
        score_field: Field name containing score
        reverse: True for descending order (highest first)
        
    Returns:
        Sorted list of items
    """
    return sorted(
        items,
        key=lambda x: x.get(score_field, 0),
        reverse=reverse
    )


def filter_by_confidence(
    items: List[Dict[str, Any]],
    confidence_field: str = "confidence",
    threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Filter items by confidence threshold.
    
    Args:
        items: List of items to filter
        confidence_field: Field name containing confidence score
        threshold: Minimum confidence threshold
        
    Returns:
        Filtered list of items
    """
    return [
        item for item in items
        if item.get(confidence_field, 0) >= threshold
    ]


def safe_get(
    data: Dict[str, Any],
    key_path: str,
    default: Any = None
) -> Any:
    """Safely get nested value from dictionary.
    
    Args:
        data: Dictionary to get value from
        key_path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found
        
    Returns:
        Value at key path or default
    """
    keys = key_path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def batch_items(items: List[Any], batch_size: int) -> List[List[Any]]:
    """Split items into batches.
    
    Args:
        items: List of items to batch
        batch_size: Size of each batch
        
    Returns:
        List of batches
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def deduplicate_items(
    items: List[Dict[str, Any]],
    key: str
) -> List[Dict[str, Any]]:
    """Remove duplicate items based on a key.
    
    Args:
        items: List of items
        key: Key to use for deduplication
        
    Returns:
        Deduplicated list
    """
    seen = set()
    unique_items = []
    
    for item in items:
        value = item.get(key)
        if value not in seen:
            seen.add(value)
            unique_items.append(item)
    
    return unique_items


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage safely.
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage (0-100)
    """
    if total == 0:
        return 0.0
    return (part / total) * 100


def normalize_score(score: float, min_val: float = 0, max_val: float = 100) -> float:
    """Normalize score to 0-1 range.
    
    Args:
        score: Score to normalize
        min_val: Minimum possible value
        max_val: Maximum possible value
        
    Returns:
        Normalized score (0-1)
    """
    if max_val == min_val:
        return 0.0
    return (score - min_val) / (max_val - min_val)


def weighted_average(
    values: List[float],
    weights: List[float]
) -> float:
    """Calculate weighted average.
    
    Args:
        values: List of values
        weights: List of weights (same length as values)
        
    Returns:
        Weighted average
    """
    if len(values) != len(weights):
        raise ValueError("Values and weights must have same length")
    
    if sum(weights) == 0:
        return 0.0
    
    return sum(v * w for v, w in zip(values, weights)) / sum(weights)
