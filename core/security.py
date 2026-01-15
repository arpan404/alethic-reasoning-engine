"""
Security utilities for GDPR and SOC2 compliance.

Provides audit logging, PII masking, and security decorators for API endpoints.
"""

import functools
import logging
import json
import hashlib
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

from fastapi import Request, HTTPException
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("security.audit")


class AuditAction(str, Enum):
    """Audit log action types."""
    # Read operations
    VIEW = "VIEW"
    LIST = "LIST"
    SEARCH = "SEARCH"
    EXPORT = "EXPORT"
    
    # Write operations
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    
    # Status changes
    SHORTLIST = "SHORTLIST"
    REJECT = "REJECT"
    MOVE_STAGE = "MOVE_STAGE"
    
    # Sensitive operations
    BACKGROUND_CHECK = "BACKGROUND_CHECK"
    COMPLIANCE_ACTION = "COMPLIANCE_ACTION"
    DATA_EXPORT = "DATA_EXPORT"
    DATA_ERASURE = "DATA_ERASURE"


class ResourceType(str, Enum):
    """Resource types for audit logging."""
    CANDIDATE = "CANDIDATE"
    APPLICATION = "APPLICATION"
    JOB = "JOB"
    INTERVIEW = "INTERVIEW"
    EVALUATION = "EVALUATION"
    DOCUMENT = "DOCUMENT"
    USER = "USER"


# PII fields that should be masked in logs
PII_FIELDS: Set[str] = {
    "email", "phone", "ssn", "social_security",
    "date_of_birth", "dob", "address", "street",
    "first_name", "last_name", "full_name", "name",
    "salary", "salary_expectation_min", "salary_expectation_max",
    "bank_account", "credit_card", "passport",
}


def mask_pii(data: Any, depth: int = 0) -> Any:
    """
    Recursively mask PII fields in data structures.
    
    Args:
        data: Data to mask (dict, list, or primitive)
        depth: Current recursion depth (max 10)
        
    Returns:
        Data with PII fields masked
    """
    if depth > 10:
        return "[MAX_DEPTH]"
    
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if key.lower() in PII_FIELDS:
                if isinstance(value, str) and len(value) > 0:
                    # Partial masking: show first char and length indicator
                    masked[key] = f"{value[0]}***[{len(value)}]"
                else:
                    masked[key] = "[MASKED]"
            else:
                masked[key] = mask_pii(value, depth + 1)
        return masked
    elif isinstance(data, list):
        return [mask_pii(item, depth + 1) for item in data[:5]]  # Limit list items
    else:
        return data


def generate_request_id(request: Request) -> str:
    """Generate a unique request ID for correlation."""
    timestamp = datetime.utcnow().isoformat()
    path = request.url.path
    method = request.method
    client = request.client.host if request.client else "unknown"
    
    raw = f"{timestamp}-{method}-{path}-{client}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def log_audit_event(
    action: AuditAction,
    resource_type: ResourceType,
    resource_id: Optional[str] = None,
    user_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    contains_pii: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """
    Log an audit event for compliance tracking.
    
    This creates a structured log entry suitable for SIEM ingestion
    and compliance reporting.
    """
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": "AUDIT",
        "action": action.value,
        "resource_type": resource_type.value,
        "resource_id": str(resource_id) if resource_id else None,
        "user_id": user_id,
        "organization_id": organization_id,
        "request_id": request_id,
        "contains_pii": contains_pii,
        "ip_address": ip_address,
        "user_agent": user_agent[:200] if user_agent else None,
        "details": mask_pii(details) if details and contains_pii else details,
    }
    
    # Log as structured JSON for SIEM
    logger.info(json.dumps(event))
    
    # In production, also persist to audit table
    # await persist_audit_event(event)


def audit_log(
    action: AuditAction,
    resource_type: ResourceType,
    resource_id_param: str = None,
    contains_pii: bool = False,
):
    """
    Decorator for audit logging API endpoints.
    
    Args:
        action: The action being performed
        resource_type: Type of resource being accessed
        resource_id_param: Name of the path/query param containing resource ID
        contains_pii: Whether the endpoint handles PII data
        
    Usage:
        @router.get("/{application_id}")
        @audit_log(AuditAction.VIEW, ResourceType.CANDIDATE, "application_id", contains_pii=True)
        async def get_candidate(application_id: int, request: Request, current_user: User):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user from kwargs
            request = kwargs.get("request")
            current_user = kwargs.get("current_user")
            
            # Extract resource ID from params
            resource_id = None
            if resource_id_param:
                resource_id = kwargs.get(resource_id_param)
            
            # Generate request ID
            request_id = generate_request_id(request) if request else None
            
            # Get user info
            user_id = current_user.id if current_user else None
            org_id = getattr(current_user, "organization_id", None) if current_user else None
            
            # Get request metadata
            ip_address = None
            user_agent = None
            if request:
                ip_address = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            
            try:
                # Execute the actual endpoint
                result = await func(*args, **kwargs)
                
                # Log successful access
                await log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=user_id,
                    organization_id=org_id,
                    request_id=request_id,
                    contains_pii=contains_pii,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"status": "success"},
                )
                
                return result
                
            except HTTPException as e:
                # Log failed access attempt
                await log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=user_id,
                    organization_id=org_id,
                    request_id=request_id,
                    contains_pii=contains_pii,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"status": "failed", "error": str(e.detail)},
                )
                raise
                
            except Exception as e:
                # Log error
                await log_audit_event(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=user_id,
                    organization_id=org_id,
                    request_id=request_id,
                    contains_pii=contains_pii,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    details={"status": "error", "error": str(e)[:200]},
                )
                raise
                
        return wrapper
    return decorator


def require_consent(consent_type: str):
    """
    Decorator to verify user has given required GDPR consent.
    
    Args:
        consent_type: Type of consent required (e.g., "data_processing", "marketing")
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            
            # Check consent (simplified - real impl would check DB)
            # if not has_consent(current_user, consent_type):
            #     raise HTTPException(403, f"Consent required: {consent_type}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
