"""Common validation functions for type-safe tool operations."""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


def validate_positive_int(value: Any, name: str) -> int:
    """Validate that a value is a positive integer.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated integer value.
        
    Raises:
        ValidationError: If value is not a positive integer.
    """
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer, got {type(value).__name__}")
    if value <= 0:
        raise ValidationError(f"{name} must be positive, got {value}")
    return value


def validate_non_negative_int(value: Any, name: str) -> int:
    """Validate that a value is a non-negative integer.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated integer value.
        
    Raises:
        ValidationError: If value is not a non-negative integer.
    """
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be an integer, got {type(value).__name__}")
    if value < 0:
        raise ValidationError(f"{name} must be non-negative, got {value}")
    return value


def validate_positive_float(value: Any, name: str) -> float:
    """Validate that a value is a positive float.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated float value.
        
    Raises:
        ValidationError: If value is not a positive number.
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
    if value <= 0:
        raise ValidationError(f"{name} must be positive, got {value}")
    return float(value)


def validate_datetime(value: Any, name: str) -> datetime:
    """Validate that a value is a datetime object.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated datetime value.
        
    Raises:
        ValidationError: If value is not a datetime object.
    """
    if not isinstance(value, datetime):
        raise ValidationError(f"{name} must be a datetime object, got {type(value).__name__}")
    return value


def validate_non_empty_string(value: Any, name: str) -> str:
    """Validate that a value is a non-empty string.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated string value.
        
    Raises:
        ValidationError: If value is not a non-empty string.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string, got {type(value).__name__}")
    if not value.strip():
        raise ValidationError(f"{name} cannot be empty")
    return value


def validate_list(value: Any, name: str, min_length: int = 0) -> List[Any]:
    """Validate that a value is a list with minimum length.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        min_length: Minimum required list length.
        
    Returns:
        Validated list value.
        
    Raises:
        ValidationError: If value is not a list or is too short.
    """
    if not isinstance(value, list):
        raise ValidationError(f"{name} must be a list, got {type(value).__name__}")
    if len(value) < min_length:
        raise ValidationError(f"{name} must have at least {min_length} items, got {len(value)}")
    return value


def validate_dict(value: Any, name: str, required_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Validate that a value is a dictionary with required keys.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        required_keys: List of keys that must be present.
        
    Returns:
        Validated dictionary value.
        
    Raises:
        ValidationError: If value is not a dict or missing required keys.
    """
    if not isinstance(value, dict):
        raise ValidationError(f"{name} must be a dictionary, got {type(value).__name__}")
    
    if required_keys:
        missing_keys = [key for key in required_keys if key not in value]
        if missing_keys:
            raise ValidationError(f"{name} missing required keys: {missing_keys}")
    
    return value


def validate_email(value: Any, name: str) -> str:
    """Validate that a value is a valid email address.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated email string.
        
    Raises:
        ValidationError: If value is not a valid email format.
    """
    value = validate_non_empty_string(value, name)
    
    # Basic email validation
    if '@' not in value or '.' not in value.split('@')[1]:
        raise ValidationError(f"{name} must be a valid email address")
    
    return value


def validate_percentage(value: Any, name: str) -> float:
    """Validate that a value is a percentage between 0 and 100.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated percentage value.
        
    Raises:
        ValidationError: If value is not between 0 and 100.
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
    if not 0 <= value <= 100:
        raise ValidationError(f"{name} must be between 0 and 100, got {value}")
    return float(value)


def validate_probability(value: Any, name: str) -> float:
    """Validate that a value is a probability between 0 and 1.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        
    Returns:
        Validated probability value.
        
    Raises:
        ValidationError: If value is not between 0 and 1.
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
    if not 0 <= value <= 1:
        raise ValidationError(f"{name} must be between 0 and 1, got {value}")
    return float(value)


def validate_enum(value: Any, name: str, valid_values: List[str]) -> str:
    """Validate that a value is one of the allowed enum values.
    
    Args:
        value: Value to validate.
        name: Parameter name for error messages.
        valid_values: List of valid string values.
        
    Returns:
        Validated string value.
        
    Raises:
        ValidationError: If value is not in valid_values.
    """
    value = validate_non_empty_string(value, name)
    
    if value not in valid_values:
        raise ValidationError(f"{name} must be one of {valid_values}, got '{value}'")
    
    return value
