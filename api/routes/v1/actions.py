"""
Direct action endpoints.

Provides REST API for quick actions triggered from UI buttons and menus.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import candidates, applications, communications

router = APIRouter(prefix="/actions", tags=["actions"])


class QuickRejectRequest(BaseModel):
    """Request model for quick rejection."""
    application_id: int = Field(..., description="Application ID")
    reason: str = Field(..., min_length=5, description="Rejection reason")
    send_email: bool = Field(True, description="Send rejection notification")


class QuickAdvanceRequest(BaseModel):
    """Request model for advancing application."""
    application_id: int = Field(..., description="Application ID")
    stage: str = Field(..., description="Target pipeline stage")


class QuickShortlistRequest(BaseModel):
    """Request model for quick shortlisting."""
    application_id: int = Field(..., description="Application ID")
    reason: Optional[str] = Field(None, description="Shortlist reason")


class SendEmailRequest(BaseModel):
    """Request model for sending email."""
    application_id: int = Field(..., description="Application ID")
    template_id: Optional[int] = Field(None, description="Email template ID")
    subject: Optional[str] = Field(None, description="Custom email subject")
    content: Optional[str] = Field(None, description="Custom email content")


@router.post(
    "/reject",
    summary="Quick Reject",
    description="Quickly reject an application. Requires application:reject permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_REJECT))],
)
async def quick_reject(
    request: QuickRejectRequest,
    current_user: User = Depends(require_active_user),
):
    """Reject an application with optional email notification."""
    result = await candidates.reject_candidate(
        application_id=request.application_id,
        reason=request.reason,
        send_notification=request.send_email,
        rejected_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/advance",
    summary="Quick Advance",
    description="Move application to next stage. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def quick_advance(
    request: QuickAdvanceRequest,
    current_user: User = Depends(require_active_user),
):
    """Move an application to the next pipeline stage."""
    result = await applications.move_application_stage(
        application_id=request.application_id,
        new_stage=request.stage,
        moved_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/shortlist",
    summary="Quick Shortlist",
    description="Add application to shortlist. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def quick_shortlist(
    request: QuickShortlistRequest,
    current_user: User = Depends(require_active_user),
):
    """Add an application to the shortlist for review."""
    result = await candidates.shortlist_candidate(
        application_id=request.application_id,
        reason=request.reason,
        shortlisted_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/send-email",
    summary="Send Email",
    description="Send email to candidate. Requires application:update permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_UPDATE))],
)
async def send_email(
    request: SendEmailRequest,
    current_user: User = Depends(require_active_user),
):
    """Send an email to a candidate using a template or custom content."""
    if not request.template_id and not (request.subject and request.content):
        raise HTTPException(
            status_code=400,
            detail="Either template_id or both subject and content are required"
        )
    
    result = await communications.send_email(
        application_id=request.application_id,
        template_id=request.template_id,
        custom_subject=request.subject,
        custom_content=request.content,
        sent_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
