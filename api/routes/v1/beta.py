"""Beta registration endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional

from database.engine import get_db
from database.models.beta_registrations import BetaRegistration, BetaStatus
from api.schemas.beta import (
    BetaRegistrationRequest,
    BetaRegistrationResponse,
    BetaRegistrationUpdate,
    BetaStatusType,
    VALID_BETA_STATUSES,
)
from api.schemas.common import PaginationParams, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/beta", tags=["beta"])



@router.post(
    "/register",
    response_model=BetaRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register for beta access",
    description="Submit application for early access to beta features",
)
async def register_for_beta(
    request: BetaRegistrationRequest,
    db: AsyncSession = Depends(get_db),
) -> BetaRegistrationResponse:
    """
    Register a user for the beta program.

    - **email**: User email address (must be unique)
    - **first_name**: First name
    - **last_name**: Last name
    - **company_name**: Optional company name
    - **job_title**: Optional job title
    - **phone**: Optional phone number
    - **use_case**: Optional description of intended use
    - **referral_source**: Optional source of referral
    - **newsletter_opt_in**: Opt in to newsletter communications
    """
    # Check if email already registered
    stmt = select(BetaRegistration).where(BetaRegistration.email == request.email)
    existing = await db.execute(stmt)
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered for beta program",
        )

    # Create new beta registration
    registration = BetaRegistration(
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        company_name=request.company_name,
        job_title=request.job_title,
        phone=request.phone,
        use_case=request.use_case,
        referral_source=request.referral_source,
        newsletter_opt_in=request.newsletter_opt_in,
        status=BetaStatus.PENDING,
    )

    db.add(registration)
    await db.commit()
    await db.refresh(registration)

    logger.info(f"New beta registration: {registration.email}")

    return BetaRegistrationResponse.model_validate(registration)


@router.get(
    "/{registration_id}",
    response_model=BetaRegistrationResponse,
    summary="Get beta registration",
    description="Retrieve a specific beta registration by ID",
)
async def get_beta_registration(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
) -> BetaRegistrationResponse:
    """Get a specific beta registration."""
    stmt = select(BetaRegistration).where(BetaRegistration.id == registration_id)
    result = await db.execute(stmt)
    registration = result.scalars().first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta registration not found",
        )

    return BetaRegistrationResponse.model_validate(registration)


@router.patch(
    "/{registration_id}",
    response_model=BetaRegistrationResponse,
    summary="Update beta registration status",
    description="Update the status of a beta registration (admin only)",
)
async def update_beta_registration(
    registration_id: int,
    update: BetaRegistrationUpdate,
    db: AsyncSession = Depends(get_db),
) -> BetaRegistrationResponse:
    """
    Update beta registration status.

    - **status**: New status (pending, approved, rejected, active, inactive)
    - **approved_at**: Optional timestamp when approved
    """
    stmt = select(BetaRegistration).where(BetaRegistration.id == registration_id)
    result = await db.execute(stmt)
    registration = result.scalars().first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta registration not found",
        )

    # Status is already validated by Pydantic schema
    registration.status = update.status
    if update.status == "approved" and not registration.approved_at:
        registration.approved_at = update.approved_at or datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(registration)

    logger.info(f"Updated beta registration {registration_id} status to {update.status}")

    return BetaRegistrationResponse.model_validate(registration)


@router.get(
    "",
    response_model=PaginatedResponse[BetaRegistrationResponse],
    summary="List beta registrations",
    description="Get list of all beta registrations (paginated, admin only)",
)
async def list_beta_registrations(
    pagination: PaginationParams = Depends(),
    status_filter: Optional[BetaStatusType] = None,
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[BetaRegistrationResponse]:
    """
    Get paginated list of beta registrations.

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status_filter**: Optional status filter (pending, approved, rejected, active, inactive)
    """
    # Build base query
    query = select(BetaRegistration).order_by(desc(BetaRegistration.created_at))
    count_query = select(func.count(BetaRegistration.id))

    # Apply status filter if provided
    if status_filter:
        if status_filter not in VALID_BETA_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Must be one of: {', '.join(VALID_BETA_STATUSES)}",
            )
        query = query.where(BetaRegistration.status == status_filter)
        count_query = count_query.where(BetaRegistration.status == status_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total: int = total_result.scalar() or 0

    # Get paginated results
    paginated_query = query.offset(pagination.offset).limit(pagination.page_size)
    result = await db.execute(paginated_query)
    registrations = result.scalars().all()

    items = [BetaRegistrationResponse.model_validate(r) for r in registrations]

    return PaginatedResponse.create(items, total, pagination)


@router.delete(
    "/{registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete beta registration",
    description="Delete a beta registration (admin only)",
)
async def delete_beta_registration(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a beta registration."""
    stmt = select(BetaRegistration).where(BetaRegistration.id == registration_id)
    result = await db.execute(stmt)
    registration = result.scalars().first()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta registration not found",
        )

    await db.delete(registration)
    await db.commit()

    logger.info(f"Deleted beta registration {registration_id}")
