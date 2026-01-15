"""Offer management API routes."""

from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import offers as offer_service

router = APIRouter(prefix="/offers", tags=["offers"])


class CreateOfferRequest(BaseModel):
    application_id: int
    salary: Decimal = Field(..., description="Base salary amount")
    salary_currency: str = Field(default="USD", max_length=3)
    start_date: Optional[str] = Field(None, description="Proposed start date (YYYY-MM-DD)")
    signing_bonus: Optional[Decimal] = None
    equity_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    benefits: Optional[List[str]] = None
    notes: Optional[str] = None


class UpdateOfferRequest(BaseModel):
    salary: Optional[Decimal] = None
    salary_currency: Optional[str] = None
    start_date: Optional[str] = None
    signing_bonus: Optional[Decimal] = None
    equity_percentage: Optional[Decimal] = None
    benefits: Optional[List[str]] = None
    notes: Optional[str] = None


class SendOfferRequest(BaseModel):
    expires_in_days: int = Field(default=7, ge=1, le=30)


class WithdrawOfferRequest(BaseModel):
    reason: str = Field(..., min_length=5)


class OfferResponseRequest(BaseModel):
    response: str = Field(..., pattern="^(accepted|declined)$")
    signature: Optional[str] = None
    notes: Optional[str] = None


@router.post("/create")
async def create_offer(
    request: CreateOfferRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Create a new job offer for an application.
    
    Creates a draft offer that can be edited before sending.
    """
    result = await offer_service.create_offer(
        application_id=request.application_id,
        salary=request.salary,
        salary_currency=request.salary_currency,
        start_date=request.start_date,
        signing_bonus=request.signing_bonus,
        equity_percentage=request.equity_percentage,
        benefits=request.benefits,
        notes=request.notes,
        created_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{offer_id}")
async def get_offer(
    offer_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get offer details."""
    result = await offer_service.get_offer(offer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Offer not found")
    return result


@router.get("")
async def list_offers(
    job_id: Optional[int] = Query(None, description="Filter by job"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """List offers with filtering."""
    result = await offer_service.list_offers(
        job_id=job_id,
        status=status,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    return result


@router.put("/{offer_id}")
async def update_offer(
    offer_id: int = Path(...),
    request: UpdateOfferRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """
    Update offer details.
    
    Only draft offers can be updated.
    """
    updates = request.model_dump(exclude_unset=True)
    result = await offer_service.update_offer(
        offer_id=offer_id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{offer_id}/send")
async def send_offer(
    offer_id: int = Path(...),
    request: SendOfferRequest = Body(default=SendOfferRequest()),
    current_user: User = Depends(require_active_user),
):
    """
    Send offer to candidate.
    
    Sends the offer email and makes it available for candidate response.
    """
    result = await offer_service.send_offer(
        offer_id=offer_id,
        expires_in_days=request.expires_in_days,
        sent_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{offer_id}/withdraw")
async def withdraw_offer(
    offer_id: int = Path(...),
    request: WithdrawOfferRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """
    Withdraw an offer.
    
    Can only withdraw offers that haven't been responded to.
    """
    result = await offer_service.withdraw_offer(
        offer_id=offer_id,
        reason=request.reason,
        withdrawn_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{offer_id}/respond")
async def record_offer_response(
    offer_id: int = Path(...),
    request: OfferResponseRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """
    Record candidate's response to offer.
    
    Used to record acceptance or decline of an offer.
    """
    result = await offer_service.record_offer_response(
        offer_id=offer_id,
        response=request.response,
        signature=request.signature,
        notes=request.notes,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
