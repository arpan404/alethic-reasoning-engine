"""Extended utility functions for agents."""

import asyncio
import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


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
