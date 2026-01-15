"""
Offer management endpoints.

Provides REST API for creating, sending, and managing job offers.
"""

from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import offers as offer_service

router = APIRouter(prefix="/offers", tags=["offers"])


class CreateOfferRequest(BaseModel):
    """Request model for creating a new offer."""
    application_id: int = Field(..., description="Application to create offer for")
    salary: Decimal = Field(..., gt=0, description="Annual base salary")
    salary_currency: str = Field("USD", min_length=3, max_length=3, description="ISO currency code")
    start_date: Optional[str] = Field(None, description="Proposed start date (YYYY-MM-DD)")
    signing_bonus: Optional[Decimal] = Field(None, ge=0, description="One-time signing bonus")
    equity_percentage: Optional[Decimal] = Field(None, ge=0, le=100, description="Equity grant percentage")
    benefits: Optional[list[str]] = Field(None, description="List of included benefits")
    notes: Optional[str] = Field(None, description="Internal notes")


class UpdateOfferRequest(BaseModel):
    """Request model for updating a draft offer."""
    salary: Optional[Decimal] = Field(None, gt=0)
    salary_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    start_date: Optional[str] = Field(None)
    signing_bonus: Optional[Decimal] = Field(None, ge=0)
    equity_percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    benefits: Optional[list[str]] = Field(None)
    notes: Optional[str] = Field(None)


class SendOfferRequest(BaseModel):
    """Request model for sending an offer."""
    expires_in_days: int = Field(7, ge=1, le=30, description="Days until offer expires")


class WithdrawOfferRequest(BaseModel):
    """Request model for withdrawing an offer."""
    reason: str = Field(..., min_length=5, description="Reason for withdrawal")


class OfferResponseRequest(BaseModel):
    """Request model for recording offer response."""
    response: str = Field(..., description="Response: 'accepted' or 'declined'")
    signature: Optional[str] = Field(None, description="Digital signature for acceptance")
    notes: Optional[str] = Field(None, description="Candidate notes")


@router.post(
    "",
    summary="Create Offer",
    description="Create a new job offer draft. Requires offer:create permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_CREATE))],
)
async def create_offer(
    request: CreateOfferRequest,
    current_user: User = Depends(require_active_user),
):
    """Create a new offer draft with compensation details."""
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


@router.get(
    "/{offer_id}",
    summary="Get Offer Details",
    description="Get detailed offer information. Requires offer:read permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_READ))],
)
async def get_offer(
    offer_id: int = Path(..., description="Offer ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve complete offer details including compensation and status."""
    result = await offer_service.get_offer(offer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Offer not found")
    return result


@router.get(
    "",
    summary="List Offers",
    description="List offers with optional filtering. Requires offer:read permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_READ))],
)
async def list_offers(
    job_id: Optional[int] = Query(None, description="Filter by job"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of offers with optional filters."""
    return await offer_service.list_offers(
        job_id=job_id,
        status=status,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )


@router.put(
    "/{offer_id}",
    summary="Update Offer",
    description="Update a draft offer. Requires offer:update permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_UPDATE))],
)
async def update_offer(
    offer_id: int = Path(..., description="Offer ID"),
    request: UpdateOfferRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Update offer details. Only draft offers can be modified."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    result = await offer_service.update_offer(
        offer_id=offer_id,
        updates=updates,
        updated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/{offer_id}/send",
    summary="Send Offer",
    description="Send offer to candidate. Requires offer:send permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_SEND))],
)
async def send_offer(
    offer_id: int = Path(..., description="Offer ID"),
    request: SendOfferRequest = Body(default=SendOfferRequest()),
    current_user: User = Depends(require_active_user),
):
    """Send a draft offer to the candidate via email with expiration date."""
    result = await offer_service.send_offer(
        offer_id=offer_id,
        expires_in_days=request.expires_in_days,
        sent_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/{offer_id}/withdraw",
    summary="Withdraw Offer",
    description="Withdraw a sent offer. Requires offer:revoke permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_REVOKE))],
)
async def withdraw_offer(
    offer_id: int = Path(..., description="Offer ID"),
    request: WithdrawOfferRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Withdraw an offer that has been sent but not yet accepted."""
    result = await offer_service.withdraw_offer(
        offer_id=offer_id,
        reason=request.reason,
        withdrawn_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/{offer_id}/respond",
    summary="Record Offer Response",
    description="Record candidate's response to offer. Requires offer:update permission.",
    dependencies=[Depends(require_permission(Permission.OFFER_UPDATE))],
)
async def record_offer_response(
    offer_id: int = Path(..., description="Offer ID"),
    request: OfferResponseRequest = Body(...),
    current_user: User = Depends(require_active_user),
):
    """Record candidate's acceptance or declination of an offer."""
    if request.response not in ["accepted", "declined"]:
        raise HTTPException(status_code=400, detail="Response must be 'accepted' or 'declined'")
    
    result = await offer_service.record_offer_response(
        offer_id=offer_id,
        response=request.response,
        signature=request.signature,
        notes=request.notes,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
