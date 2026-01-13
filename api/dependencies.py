"""FastAPI dependencies for dependency injection."""

from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from database.engine import get_db
from database.models.users import User, UserSession
from core.config import settings
from core.security import decode_token


security = HTTPBearer()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token or session.
    This is optional - returns None if not authenticated.
    """
    # Try to get user from request state (set by authentication middleware)
    if hasattr(request.state, 'user') and request.state.user:
        return request.state.user
    
    return None


async def require_authenticated_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require user to be authenticated."""
    user = await get_current_user(request, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def require_active_user(
    current_user: User = Depends(require_authenticated_user),
) -> User:
    """Require user to be active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


async def require_verified_email(
    current_user: User = Depends(require_active_user),
) -> User:
    """Require user to have verified email."""
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return current_user


async def require_admin_user(
    current_user: User = Depends(require_active_user),
) -> User:
    """Require user to be an admin."""
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_recruiter_or_admin(
    current_user: User = Depends(require_active_user),
) -> User:
    """Require user to be a recruiter or admin."""
    if current_user.user_type not in ["recruiter", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter or admin access required",
        )
    return current_user


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for endpoints that work both authenticated and unauthenticated.
    """
    try:
        return await get_current_user(request, db)
    except:
        return None


def get_pagination_params(
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
) -> dict:
    """
    Get pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Dictionary with offset and limit
    """
    # Validate page
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be >= 1"
        )
    
    # Validate and cap page_size
    if page_size < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page size must be >= 1"
        )
    
    if page_size > max_page_size:
        page_size = max_page_size
    
    # Calculate offset
    offset = (page - 1) * page_size
    
    return {
        "offset": offset,
        "limit": page_size,
        "page": page,
        "page_size": page_size
    }

