"""User management API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = None


class DeactivateUserRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/me")
async def get_current_user(
    current_user: User = Depends(require_active_user),
):
    """Get current user's profile."""
    result = await user_service.get_user(current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/me")
async def update_current_user(
    request: UpdateProfileRequest,
    current_user: User = Depends(require_active_user),
):
    """Update current user's profile."""
    updates = request.model_dump(exclude_unset=True)
    result = await user_service.update_user(
        user_id=current_user.id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("")
async def list_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """
    List organization users.
    
    Requires admin permissions.
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    result = await user_service.list_users(
        organization_id=current_user.organization_id,
        role=role,
        status=status,
        search_query=search,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/{user_id}")
async def get_user(
    user_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """
    Get user details.
    
    Requires admin permissions to view other users.
    """
    result = await user_service.get_user(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result


@router.put("/{user_id}")
async def update_user(
    user_id: int = Path(...),
    request: UpdateProfileRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """
    Update user details.
    
    Requires admin permissions to update other users.
    """
    updates = request.model_dump(exclude_unset=True)
    result = await user_service.update_user(
        user_id=user_id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int = Path(...),
    request: DeactivateUserRequest = Body(default=DeactivateUserRequest()),
    current_user: User = Depends(require_active_user),
):
    """
    Deactivate a user account.
    
    Requires admin permissions.
    """
    result = await user_service.deactivate_user(
        user_id=user_id,
        reason=request.reason,
        deactivated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{user_id}/permissions")
async def get_user_permissions(
    user_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get permissions for a user."""
    result = await user_service.get_user_permissions(user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
