"""
Webhook management endpoints.

Provides REST API for configuring and managing webhook integrations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import webhooks as webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

AVAILABLE_EVENTS = [
    "application.created",
    "application.updated",
    "application.stage_changed",
    "application.rejected",
    "candidate.created",
    "candidate.updated",
    "interview.scheduled",
    "interview.completed",
    "interview.cancelled",
    "offer.created",
    "offer.sent",
    "offer.accepted",
    "offer.declined",
    "offer.withdrawn",
    "evaluation.completed",
]


class RegisterWebhookRequest(BaseModel):
    """Request model for registering a webhook."""
    name: Optional[str] = Field(None, max_length=100, description="Webhook display name")
    url: str = Field(..., description="Webhook endpoint URL (https required)")
    events: list[str] = Field(..., min_length=1, description="List of events to subscribe to")
    secret: Optional[str] = Field(None, description="Signing secret (auto-generated if not provided)")


class UpdateWebhookRequest(BaseModel):
    """Request model for updating a webhook."""
    name: Optional[str] = Field(None, max_length=100)
    url: Optional[str] = Field(None)
    events: Optional[list[str]] = Field(None, min_length=1)
    status: Optional[str] = Field(None, description="Status: active, paused")


@router.get(
    "/events",
    summary="List Available Events",
    description="Get list of available webhook event types.",
)
async def list_available_events(
    current_user: User = Depends(require_active_user),
):
    """Retrieve the list of all available webhook event types."""
    return {"events": AVAILABLE_EVENTS}


@router.post(
    "",
    summary="Register Webhook",
    description="Register a new webhook endpoint. Requires settings:edit permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_EDIT))],
)
async def register_webhook(
    request: RegisterWebhookRequest,
    current_user: User = Depends(require_active_user),
):
    """Register a new webhook to receive event notifications."""
    if not request.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Webhook URL must use HTTPS")
    
    invalid_events = set(request.events) - set(AVAILABLE_EVENTS)
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}"
        )
    
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    result = await webhook_service.register_webhook(
        organization_id=current_user.organization_id,
        url=request.url,
        events=request.events,
        secret=request.secret,
        name=request.name,
        created_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "",
    summary="List Webhooks",
    description="List registered webhooks. Requires settings:view permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_VIEW))],
)
async def list_webhooks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of registered webhooks."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    return await webhook_service.list_webhooks(
        organization_id=current_user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{webhook_id}",
    summary="Get Webhook",
    description="Get webhook details. Requires settings:view permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_VIEW))],
)
async def get_webhook(
    webhook_id: int = Path(..., description="Webhook ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve detailed information about a webhook including secret."""
    result = await webhook_service.get_webhook(webhook_id)
    if not result:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return result


@router.put(
    "/{webhook_id}",
    summary="Update Webhook",
    description="Update webhook configuration. Requires settings:edit permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_EDIT))],
)
async def update_webhook(
    webhook_id: int = Path(..., description="Webhook ID"),
    request: UpdateWebhookRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Update webhook URL, events, or status."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    if "url" in updates and not updates["url"].startswith("https://"):
        raise HTTPException(status_code=400, detail="Webhook URL must use HTTPS")
    
    if "events" in updates:
        invalid_events = set(updates["events"]) - set(AVAILABLE_EVENTS)
        if invalid_events:
            raise HTTPException(status_code=400, detail=f"Invalid events: {invalid_events}")
    
    result = await webhook_service.update_webhook(
        webhook_id=webhook_id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete(
    "/{webhook_id}",
    summary="Delete Webhook",
    description="Delete a webhook. Requires settings:edit permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_EDIT))],
)
async def delete_webhook(
    webhook_id: int = Path(..., description="Webhook ID"),
    current_user: User = Depends(require_active_user),
):
    """Permanently delete a webhook registration."""
    result = await webhook_service.delete_webhook(
        webhook_id=webhook_id,
        deleted_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/{webhook_id}/test",
    summary="Test Webhook",
    description="Send a test request to webhook endpoint. Requires settings:edit permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_EDIT))],
)
async def test_webhook(
    webhook_id: int = Path(..., description="Webhook ID"),
    current_user: User = Depends(require_active_user),
):
    """Send a test payload to verify webhook endpoint connectivity."""
    result = await webhook_service.test_webhook(webhook_id)
    return result


@router.get(
    "/{webhook_id}/deliveries",
    summary="Get Webhook Deliveries",
    description="Get delivery history for a webhook. Requires settings:view permission.",
    dependencies=[Depends(require_permission(Permission.SETTINGS_VIEW))],
)
async def get_webhook_deliveries(
    webhook_id: int = Path(..., description="Webhook ID"),
    status: Optional[str] = Query(None, description="Filter by delivery status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve delivery history showing success/failure status for each event."""
    return await webhook_service.get_webhook_deliveries(
        webhook_id=webhook_id,
        status=status,
        limit=limit,
        offset=offset,
    )
