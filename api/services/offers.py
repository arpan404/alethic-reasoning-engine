"""
Offer service functions for API endpoints.

Provides direct database operations for offer management,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.offers import Offer, OfferStatus
from database.models.applications import Application, ApplicationActivity, ApplicationActivityType
from database.models.candidates import Candidate
from database.models.jobs import Job

logger = logging.getLogger(__name__)


async def create_offer(
    application_id: int,
    salary: Decimal,
    salary_currency: str = "USD",
    start_date: Optional[str] = None,
    signing_bonus: Optional[Decimal] = None,
    equity_percentage: Optional[Decimal] = None,
    benefits: Optional[List[str]] = None,
    notes: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a new job offer for an application.
    
    Args:
        application_id: The application to create offer for
        salary: Base salary amount
        salary_currency: Currency code
        start_date: Proposed start date
        signing_bonus: Optional signing bonus
        equity_percentage: Optional equity
        benefits: List of benefits
        notes: Additional notes
        created_by: User ID who created
        
    Returns:
        Dictionary with offer details
    """
    async with AsyncSessionLocal() as session:
        # Get application
        result = await session.execute(
            select(Application)
            .options(
                selectinload(Application.candidate),
                selectinload(Application.job),
            )
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
        
        # Parse start date
        parsed_start_date = None
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
        
        # Create offer
        offer = Offer(
            application_id=application_id,
            candidate_id=application.candidate_id,
            job_id=application.job_id,
            salary=salary,
            salary_currency=salary_currency,
            start_date=parsed_start_date,
            signing_bonus=signing_bonus,
            equity_percentage=equity_percentage,
            benefits=benefits or [],
            notes=notes,
            status=OfferStatus.DRAFT,
            created_by_id=created_by,
        )
        session.add(offer)
        await session.flush()
        
        # Record activity
        activity = ApplicationActivity(
            application_id=application_id,
            activity_type=ApplicationActivityType.OFFER_CREATED,
            performed_by_id=created_by,
            details={"offer_id": offer.id, "salary": str(salary)},
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "offer_id": offer.id,
            "application_id": application_id,
            "status": "draft",
            "salary": str(salary),
            "salary_currency": salary_currency,
        }


async def get_offer(offer_id: int) -> Optional[Dict[str, Any]]:
    """
    Get offer details.
    
    Args:
        offer_id: The offer ID
        
    Returns:
        Dictionary with offer details or None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Offer)
            .options(
                selectinload(Offer.application).selectinload(Application.candidate),
                selectinload(Offer.job),
            )
            .where(Offer.id == offer_id)
        )
        offer = result.scalar_one_or_none()
        
        if not offer:
            return None
        
        candidate_name = None
        if offer.application and offer.application.candidate:
            c = offer.application.candidate
            candidate_name = f"{c.first_name} {c.last_name}"
        
        return {
            "id": offer.id,
            "application_id": offer.application_id,
            "candidate_name": candidate_name,
            "job_title": offer.job.title if offer.job else None,
            "status": offer.status.value if hasattr(offer.status, 'value') else str(offer.status),
            "salary": str(offer.salary) if offer.salary else None,
            "salary_currency": offer.salary_currency,
            "start_date": offer.start_date.isoformat() if offer.start_date else None,
            "signing_bonus": str(offer.signing_bonus) if offer.signing_bonus else None,
            "equity_percentage": str(offer.equity_percentage) if offer.equity_percentage else None,
            "benefits": offer.benefits or [],
            "notes": offer.notes,
            "created_at": offer.created_at.isoformat() if offer.created_at else None,
            "sent_at": offer.sent_at.isoformat() if hasattr(offer, 'sent_at') and offer.sent_at else None,
            "expires_at": offer.expires_at.isoformat() if hasattr(offer, 'expires_at') and offer.expires_at else None,
            "responded_at": offer.responded_at.isoformat() if hasattr(offer, 'responded_at') and offer.responded_at else None,
        }


async def list_offers(
    job_id: Optional[int] = None,
    status: Optional[str] = None,
    organization_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    List offers with filtering.
    
    Args:
        job_id: Filter by job
        status: Filter by status
        organization_id: Filter by organization
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        Dictionary with offers list
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Offer)
            .options(
                selectinload(Offer.application).selectinload(Application.candidate),
                selectinload(Offer.job),
            )
        )
        
        if job_id:
            query = query.where(Offer.job_id == job_id)
        if status:
            try:
                status_enum = OfferStatus(status)
                query = query.where(Offer.status == status_enum)
            except ValueError:
                pass
        
        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Offer.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        offers = result.scalars().all()
        
        offer_list = []
        for offer in offers:
            candidate_name = None
            if offer.application and offer.application.candidate:
                c = offer.application.candidate
                candidate_name = f"{c.first_name} {c.last_name}"
            
            offer_list.append({
                "id": offer.id,
                "application_id": offer.application_id,
                "candidate_name": candidate_name,
                "job_title": offer.job.title if offer.job else None,
                "status": offer.status.value if hasattr(offer.status, 'value') else str(offer.status),
                "salary": str(offer.salary) if offer.salary else None,
                "created_at": offer.created_at.isoformat() if offer.created_at else None,
            })
        
        return {
            "offers": offer_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def update_offer(
    offer_id: int,
    updates: Dict[str, Any],
    updated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Update offer details.
    
    Args:
        offer_id: The offer to update
        updates: Dictionary of fields to update
        updated_by: User ID who updated
        
    Returns:
        Dictionary with success status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Offer).where(Offer.id == offer_id)
        )
        offer = result.scalar_one_or_none()
        
        if not offer:
            return {"success": False, "error": "Offer not found"}
        
        # Only allow updates on draft offers
        if offer.status != OfferStatus.DRAFT:
            return {"success": False, "error": "Can only update draft offers"}
        
        # Apply updates
        allowed_fields = ["salary", "salary_currency", "start_date", "signing_bonus", 
                         "equity_percentage", "benefits", "notes"]
        
        for field in allowed_fields:
            if field in updates:
                if field == "start_date" and updates[field]:
                    try:
                        setattr(offer, field, datetime.strptime(updates[field], "%Y-%m-%d"))
                    except ValueError:
                        pass
                else:
                    setattr(offer, field, updates[field])
        
        await session.commit()
        
        return {
            "success": True,
            "offer_id": offer_id,
            "updated_fields": list(updates.keys()),
        }


async def send_offer(
    offer_id: int,
    expires_in_days: int = 7,
    sent_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Send offer to candidate.
    
    Args:
        offer_id: The offer to send
        expires_in_days: Days until offer expires
        sent_by: User ID who sent
        
    Returns:
        Dictionary with send status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Offer)
            .options(selectinload(Offer.application).selectinload(Application.candidate))
            .where(Offer.id == offer_id)
        )
        offer = result.scalar_one_or_none()
        
        if not offer:
            return {"success": False, "error": "Offer not found"}
        
        if offer.status != OfferStatus.DRAFT:
            return {"success": False, "error": "Offer has already been sent"}
        
        from datetime import timedelta
        
        offer.status = OfferStatus.SENT
        offer.sent_at = datetime.utcnow()
        offer.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Record activity
        activity = ApplicationActivity(
            application_id=offer.application_id,
            activity_type=ApplicationActivityType.OFFER_SENT,
            performed_by_id=sent_by,
            details={"offer_id": offer_id},
        )
        session.add(activity)
        
        await session.commit()
        
        # Queue email notification
        email_queued = False
        if offer.application and offer.application.candidate:
            try:
                from workers.tasks import queue_offer_email
                await queue_offer_email(offer_id)
                email_queued = True
            except Exception as e:
                logger.warning(f"Failed to queue offer email: {e}")
        
        return {
            "success": True,
            "offer_id": offer_id,
            "status": "sent",
            "expires_at": offer.expires_at.isoformat(),
            "email_queued": email_queued,
        }


async def withdraw_offer(
    offer_id: int,
    reason: str,
    withdrawn_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Withdraw an offer.
    
    Args:
        offer_id: The offer to withdraw
        reason: Reason for withdrawal
        withdrawn_by: User ID who withdrew
        
    Returns:
        Dictionary with withdrawal status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Offer).where(Offer.id == offer_id)
        )
        offer = result.scalar_one_or_none()
        
        if not offer:
            return {"success": False, "error": "Offer not found"}
        
        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.DECLINED]:
            return {"success": False, "error": "Cannot withdraw responded offer"}
        
        offer.status = OfferStatus.WITHDRAWN
        offer.withdrawal_reason = reason
        
        # Record activity
        activity = ApplicationActivity(
            application_id=offer.application_id,
            activity_type=ApplicationActivityType.OFFER_WITHDRAWN,
            performed_by_id=withdrawn_by,
            details={"offer_id": offer_id, "reason": reason},
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "offer_id": offer_id,
            "status": "withdrawn",
        }


async def record_offer_response(
    offer_id: int,
    response: str,
    signature: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record candidate's response to offer.
    
    Args:
        offer_id: The offer ID
        response: Response ('accepted' or 'declined')
        signature: Digital signature if accepted
        notes: Additional notes
        
    Returns:
        Dictionary with response status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Offer).where(Offer.id == offer_id)
        )
        offer = result.scalar_one_or_none()
        
        if not offer:
            return {"success": False, "error": "Offer not found"}
        
        if offer.status != OfferStatus.SENT:
            return {"success": False, "error": "Offer is not in sent status"}
        
        if response == "accepted":
            offer.status = OfferStatus.ACCEPTED
            offer.signature = signature
            activity_type = ApplicationActivityType.OFFER_ACCEPTED
        elif response == "declined":
            offer.status = OfferStatus.DECLINED
            offer.decline_notes = notes
            activity_type = ApplicationActivityType.OFFER_DECLINED
        else:
            return {"success": False, "error": "Invalid response. Use 'accepted' or 'declined'"}
        
        offer.responded_at = datetime.utcnow()
        
        # Record activity
        activity = ApplicationActivity(
            application_id=offer.application_id,
            activity_type=activity_type,
            details={"offer_id": offer_id, "response": response},
        )
        session.add(activity)
        
        await session.commit()
        
        return {
            "success": True,
            "offer_id": offer_id,
            "response": response,
            "status": offer.status.value if hasattr(offer.status, 'value') else str(offer.status),
        }
