"""
Webhook service functions for API endpoints.

Provides direct database operations for webhook management,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid
import hashlib
import hmac

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.integrations import Webhook, WebhookDelivery, WebhookStatus

logger = logging.getLogger(__name__)


async def register_webhook(
    organization_id: int,
    url: str,
    events: List[str],
    secret: Optional[str] = None,
    name: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Register a new webhook.
    
    Args:
        organization_id: The organization ID
        url: Webhook endpoint URL
        events: List of events to subscribe to
        secret: Optional signing secret (generated if not provided)
        name: Optional webhook name
        created_by: User ID who created
        
    Returns:
        Dictionary with webhook details
    """
    # Generate secret if not provided
    if not secret:
        secret = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    
    async with AsyncSessionLocal() as session:
        webhook = Webhook(
            organization_id=organization_id,
            name=name or f"Webhook {datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            url=url,
            events=events,
            secret=secret,
            status=WebhookStatus.ACTIVE,
            created_by_id=created_by,
        )
        session.add(webhook)
        await session.commit()
        
        return {
            "success": True,
            "webhook_id": webhook.id,
            "name": webhook.name,
            "url": url,
            "events": events,
            "secret": secret,
            "status": "active",
        }


async def list_webhooks(
    organization_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List webhooks for an organization.
    
    Args:
        organization_id: The organization ID
        status: Filter by status
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        Dictionary with webhooks list
    """
    async with AsyncSessionLocal() as session:
        query = select(Webhook).where(Webhook.organization_id == organization_id)
        
        if status:
            try:
                status_enum = WebhookStatus(status)
                query = query.where(Webhook.status == status_enum)
            except ValueError:
                pass
        
        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Webhook.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        webhooks = result.scalars().all()
        
        webhook_list = []
        for wh in webhooks:
            webhook_list.append({
                "id": wh.id,
                "name": wh.name,
                "url": wh.url,
                "events": wh.events,
                "status": wh.status.value if hasattr(wh.status, 'value') else str(wh.status),
                "created_at": wh.created_at.isoformat() if wh.created_at else None,
                "last_triggered": wh.last_triggered.isoformat() if hasattr(wh, 'last_triggered') and wh.last_triggered else None,
            })
        
        return {
            "webhooks": webhook_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def get_webhook(webhook_id: int) -> Optional[Dict[str, Any]]:
    """
    Get webhook details.
    
    Args:
        webhook_id: The webhook ID
        
    Returns:
        Dictionary with webhook details or None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            return None
        
        return {
            "id": webhook.id,
            "name": webhook.name,
            "url": webhook.url,
            "events": webhook.events,
            "status": webhook.status.value if hasattr(webhook.status, 'value') else str(webhook.status),
            "secret": webhook.secret,
            "created_at": webhook.created_at.isoformat() if webhook.created_at else None,
            "last_triggered": webhook.last_triggered.isoformat() if hasattr(webhook, 'last_triggered') and webhook.last_triggered else None,
            "success_count": webhook.success_count if hasattr(webhook, 'success_count') else 0,
            "failure_count": webhook.failure_count if hasattr(webhook, 'failure_count') else 0,
        }


async def update_webhook(
    webhook_id: int,
    updates: Dict[str, Any],
    updated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Update webhook configuration.
    
    Args:
        webhook_id: The webhook to update
        updates: Dictionary of fields to update
        updated_by: User ID who updated
        
    Returns:
        Dictionary with success status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
        
        # Apply allowed updates
        allowed_fields = ["name", "url", "events", "status"]
        
        for field in allowed_fields:
            if field in updates:
                if field == "status":
                    try:
                        webhook.status = WebhookStatus(updates[field])
                    except ValueError:
                        pass
                else:
                    setattr(webhook, field, updates[field])
        
        webhook.updated_at = datetime.utcnow()
        
        await session.commit()
        
        return {
            "success": True,
            "webhook_id": webhook_id,
            "updated_fields": [f for f in allowed_fields if f in updates],
        }


async def delete_webhook(
    webhook_id: int,
    deleted_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Delete a webhook.
    
    Args:
        webhook_id: The webhook to delete
        deleted_by: User ID who deleted
        
    Returns:
        Dictionary with success status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
        
        await session.delete(webhook)
        await session.commit()
        
        return {
            "success": True,
            "webhook_id": webhook_id,
            "deleted": True,
        }


async def test_webhook(webhook_id: int) -> Dict[str, Any]:
    """
    Send a test request to webhook endpoint.
    
    Args:
        webhook_id: The webhook to test
        
    Returns:
        Dictionary with test result
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
    
    # Send test request
    import httpx
    
    test_payload = {
        "event": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_id": webhook_id,
        "data": {
            "message": "This is a test webhook delivery",
        },
    }
    
    # Generate signature
    payload_bytes = str(test_payload).encode('utf-8')
    signature = hmac.new(
        webhook.secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=test_payload,
                headers={
                    "X-Webhook-Signature": signature,
                    "Content-Type": "application/json",
                },
            )
        
        return {
            "success": response.status_code < 400,
            "webhook_id": webhook_id,
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Webhook test failed: {e}")
        return {
            "success": False,
            "webhook_id": webhook_id,
            "error": str(e),
        }


async def get_webhook_deliveries(
    webhook_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Get delivery history for a webhook.
    
    Args:
        webhook_id: The webhook ID
        status: Filter by delivery status
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        Dictionary with deliveries list
    """
    async with AsyncSessionLocal() as session:
        query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook_id)
        
        if status:
            query = query.where(WebhookDelivery.status == status)
        
        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(WebhookDelivery.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        deliveries = result.scalars().all()
        
        delivery_list = []
        for d in deliveries:
            delivery_list.append({
                "id": d.id,
                "event": d.event,
                "status": d.status,
                "status_code": d.status_code if hasattr(d, 'status_code') else None,
                "response_time_ms": d.response_time_ms if hasattr(d, 'response_time_ms') else None,
                "error": d.error if hasattr(d, 'error') else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "attempts": d.attempts if hasattr(d, 'attempts') else 1,
            })
        
        return {
            "webhook_id": webhook_id,
            "deliveries": delivery_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
