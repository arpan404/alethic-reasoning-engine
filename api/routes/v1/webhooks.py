"""Webhook management API routes."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field, HttpUrl

from api.dependencies import require_active_user
from database.models.users import User
from api.services import webhooks as webhook_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class RegisterWebhookRequest(BaseModel):
    url: str = Field(..., description="Webhook endpoint URL")
    events: List[str] = Field(..., min_length=1, description="Events to subscribe to")
    name: Optional[str] = Field(None, max_length=100)
    secret: Optional[str] = Field(None, description="Signing secret (generated if not provided)")


class UpdateWebhookRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(active|paused|disabled)$")


# Available webhook events
WEBHOOK_EVENTS = [
    "application.created",
    "application.updated",
    "application.stage_changed",
    "application.rejected",
    "application.shortlisted",
    "interview.scheduled",
    "interview.completed",
    "interview.cancelled",
    "offer.created",
    "offer.sent",
    "offer.accepted",
    "offer.declined",
    "offer.withdrawn",
    "evaluation.completed",
    "candidate.created",
]


@router.get("/events")
async def list_available_events(
    current_user: User = Depends(require_active_user),
):
    """List available webhook events."""
    return {
        "events": WEBHOOK_EVENTS,
        "total": len(WEBHOOK_EVENTS),
    }


@router.post("")
async def register_webhook(
    request: RegisterWebhookRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Register a new webhook.
    
    Creates a webhook endpoint that will receive POST requests
    when specified events occur.
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    # Validate events
    invalid_events = [e for e in request.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid events: {invalid_events}"
        )
    
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


@router.get("")
async def list_webhooks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """List organization webhooks."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    result = await webhook_service.list_webhooks(
        organization_id=current_user.organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get webhook details."""
    result = await webhook_service.get_webhook(webhook_id)
    if not result:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return result


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: int = Path(...),
    request: UpdateWebhookRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Update webhook configuration."""
    updates = request.model_dump(exclude_unset=True)
    
    # Validate events if provided
    if "events" in updates:
        invalid_events = [e for e in updates["events"] if e not in WEBHOOK_EVENTS]
        if invalid_events:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid events: {invalid_events}"
            )
    
    result = await webhook_service.update_webhook(
        webhook_id=webhook_id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Delete a webhook."""
    result = await webhook_service.delete_webhook(
        webhook_id=webhook_id,
        deleted_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """
    Send a test request to webhook endpoint.
    
    Sends a test payload to verify the webhook is properly configured.
    """
    result = await webhook_service.test_webhook(webhook_id)
    return result


@router.get("/{webhook_id}/deliveries")
async def get_webhook_deliveries(
    webhook_id: int = Path(...),
    status: Optional[str] = Query(None, description="Filter by delivery status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Get delivery history for a webhook."""
    result = await webhook_service.get_webhook_deliveries(
        webhook_id=webhook_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return result
