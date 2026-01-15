"""
User management endpoints.

Provides REST API for user profile management and permissions.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


class UpdateUserRequest(BaseModel):
    """Request model for updating user profile."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None)


class DeactivateUserRequest(BaseModel):
    """Request model for deactivating a user."""
    reason: Optional[str] = Field(None, description="Reason for deactivation")


@router.get(
    "/me",
    summary="Get Current User",
    description="Get the current authenticated user's profile.",
)
async def get_current_user_profile(
    current_user: User = Depends(require_active_user),
):
    """Retrieve the current user's profile information."""
    result = await user_service.get_user(current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put(
    "/me",
    summary="Update Current User",
    description="Update the current authenticated user's profile.",
)
async def update_current_user(
    request: UpdateUserRequest,
    current_user: User = Depends(require_active_user),
):
    """Update the current user's profile information."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await user_service.update_user(
        user_id=current_user.id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "",
    summary="List Users",
    description="List users in the organization. Requires user:manage permission.",
    dependencies=[Depends(require_permission(Permission.USER_MANAGE))],
)
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of users in the organization."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    return await user_service.list_users(
        organization_id=current_user.organization_id,
        role=role,
        status=status,
        search_query=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{user_id}",
    summary="Get User",
    description="Get a specific user's profile. Requires user:manage permission.",
    dependencies=[Depends(require_permission(Permission.USER_MANAGE))],
)
async def get_user(
    user_id: int = Path(..., description="User ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a specific user's profile information."""
    result = await user_service.get_user(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put(
    "/{user_id}",
    summary="Update User",
    description="Update a user's profile. Requires user:manage permission.",
    dependencies=[Depends(require_permission(Permission.USER_MANAGE))],
)
async def update_user(
    user_id: int = Path(..., description="User ID"),
    request: UpdateUserRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Update a user's profile information."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await user_service.update_user(
        user_id=user_id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete(
    "/{user_id}",
    summary="Deactivate User",
    description="Deactivate a user account. Requires user:remove permission.",
    dependencies=[Depends(require_permission(Permission.USER_REMOVE))],
)
async def deactivate_user(
    user_id: int = Path(..., description="User ID"),
    request: DeactivateUserRequest = Body(default=DeactivateUserRequest()),
    current_user: User = Depends(require_active_user),
):
    """Deactivate a user account (soft delete)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    result = await user_service.deactivate_user(
        user_id=user_id,
        reason=request.reason,
        deactivated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "/{user_id}/permissions",
    summary="Get User Permissions",
    description="Get permissions for a user. Requires user:manage permission.",
    dependencies=[Depends(require_permission(Permission.USER_MANAGE))],
)
async def get_user_permissions(
    user_id: int = Path(..., description="User ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve the permission set for a user based on their role."""
    result = await user_service.get_user_permissions(user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
