"""
User service functions for API endpoints.

Provides direct database operations for user management,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.users import User, UserRole, UserStatus

logger = logging.getLogger(__name__)


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user details.
    
    Args:
        user_id: The user ID
        
    Returns:
        Dictionary with user details or None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
            "status": user.status.value if hasattr(user.status, 'value') else str(user.status),
            "organization_id": user.organization_id,
            "avatar_url": user.avatar_url if hasattr(user, 'avatar_url') else None,
            "phone": user.phone if hasattr(user, 'phone') else None,
            "timezone": user.timezone if hasattr(user, 'timezone') else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if hasattr(user, 'last_login') and user.last_login else None,
        }


async def list_users(
    organization_id: int,
    role: Optional[str] = None,
    status: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List users for an organization.
    
    Args:
        organization_id: The organization ID
        role: Filter by role
        status: Filter by status
        search_query: Search by name or email
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        Dictionary with users list
    """
    async with AsyncSessionLocal() as session:
        query = select(User).where(User.organization_id == organization_id)
        
        if role:
            try:
                role_enum = UserRole(role)
                query = query.where(User.role == role_enum)
            except ValueError:
                pass
        
        if status:
            try:
                status_enum = UserStatus(status)
                query = query.where(User.status == status_enum)
            except ValueError:
                pass
        
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.where(
                func.concat(User.first_name, ' ', User.last_name, ' ', User.email).ilike(search_pattern)
            )
        
        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(User.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        users = result.scalars().all()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "status": user.status.value if hasattr(user.status, 'value') else str(user.status),
                "created_at": user.created_at.isoformat() if user.created_at else None,
            })
        
        return {
            "users": user_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def update_user(
    user_id: int,
    updates: Dict[str, Any],
    updated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Update user profile.
    
    Args:
        user_id: The user to update
        updates: Dictionary of fields to update
        updated_by: User ID who made the update
        
    Returns:
        Dictionary with success status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Apply allowed updates
        allowed_fields = ["first_name", "last_name", "phone", "timezone", "avatar_url"]
        
        for field in allowed_fields:
            if field in updates:
                setattr(user, field, updates[field])
        
        user.updated_at = datetime.utcnow()
        
        await session.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "updated_fields": [f for f in allowed_fields if f in updates],
        }


async def deactivate_user(
    user_id: int,
    reason: Optional[str] = None,
    deactivated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Deactivate a user account.
    
    Args:
        user_id: The user to deactivate
        reason: Reason for deactivation
        deactivated_by: User ID who deactivated
        
    Returns:
        Dictionary with success status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.status == UserStatus.INACTIVE:
            return {"success": False, "error": "User is already inactive"}
        
        user.status = UserStatus.INACTIVE
        user.deactivated_at = datetime.utcnow()
        user.deactivation_reason = reason
        
        await session.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "status": "inactive",
        }


async def get_user_permissions(user_id: int) -> Dict[str, Any]:
    """
    Get permissions for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        Dictionary with permissions
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"error": "User not found"}
        
        # Define role-based permissions
        role_permissions = {
            "admin": [
                "users.read", "users.write", "users.delete",
                "jobs.read", "jobs.write", "jobs.delete",
                "applications.read", "applications.write",
                "offers.read", "offers.write", "offers.send",
                "reports.read", "reports.generate",
                "settings.read", "settings.write",
            ],
            "recruiter": [
                "jobs.read", "jobs.write",
                "applications.read", "applications.write",
                "offers.read", "offers.write", "offers.send",
                "reports.read",
            ],
            "hiring_manager": [
                "jobs.read",
                "applications.read", "applications.write",
                "offers.read",
            ],
            "interviewer": [
                "applications.read",
                "interviews.read", "interviews.feedback",
            ],
            "viewer": [
                "jobs.read",
                "applications.read",
            ],
        }
        
        role_value = user.role.value if hasattr(user.role, 'value') else str(user.role)
        permissions = role_permissions.get(role_value, [])
        
        return {
            "user_id": user_id,
            "role": role_value,
            "permissions": permissions,
        }
