"""Webhook service functions."""

from typing import Any, Optional
from datetime import datetime
import logging
import uuid
import hashlib
import hmac

from sqlalchemy import select, func

from database.engine import AsyncSessionLocal
from database.models.integrations import Webhook, WebhookDelivery, WebhookStatus

logger = logging.getLogger(__name__)


async def register_webhook(
    organization_id: int,
    url: str,
    events: list[str],
    secret: Optional[str] = None,
    name: Optional[str] = None,
    created_by: Optional[int] = None,
) -> dict[str, Any]:
    """Register a new webhook."""
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
) -> dict[str, Any]:
    """List webhooks for an organization."""
    async with AsyncSessionLocal() as session:
        query = select(Webhook).where(Webhook.organization_id == organization_id)
        
        if status:
            try:
                status_enum = WebhookStatus(status)
                query = query.where(Webhook.status == status_enum)
            except ValueError:
                pass
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Webhook.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        webhooks = result.scalars().all()
        
        webhook_list: list[dict[str, Any]] = []
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


async def get_webhook(webhook_id: int) -> Optional[dict[str, Any]]:
    """Get webhook details."""
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
    updates: dict[str, Any],
    updated_by: Optional[int] = None,
) -> dict[str, Any]:
    """Update webhook configuration."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
        
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
) -> dict[str, Any]:
    """Delete a webhook."""
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


async def test_webhook(webhook_id: int) -> dict[str, Any]:
    """Send a test request to webhook endpoint."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            return {"success": False, "error": "Webhook not found"}
    
    import httpx
    
    test_payload: dict[str, Any] = {
        "event": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_id": webhook_id,
        "data": {"message": "This is a test webhook delivery"},
    }
    
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
) -> dict[str, Any]:
    """Get delivery history for a webhook."""
    async with AsyncSessionLocal() as session:
        query = select(WebhookDelivery).where(WebhookDelivery.webhook_id == webhook_id)
        
        if status:
            query = query.where(WebhookDelivery.status == status)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(WebhookDelivery.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        deliveries = result.scalars().all()
        
        delivery_list: list[dict[str, Any]] = []
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
