"""
Compliance and data privacy endpoints.

Provides REST API for GDPR, FCRA, and EEO compliance requirements.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query
from pydantic import BaseModel, Field

from api.dependencies import require_active_user, require_admin_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import compliance as compliance_service

router = APIRouter(prefix="/compliance", tags=["compliance"])


class AdverseActionRequest(BaseModel):
    """Request model for adverse action notice."""
    application_id: int = Field(..., description="Application ID")
    reason: str = Field(..., min_length=10, description="Detailed reason for adverse action")
    notice_type: str = Field("pre", description="Notice type: 'pre' or 'final'")


class WorkAuthorizationRequest(BaseModel):
    """Request model for work authorization verification."""
    application_id: int = Field(..., description="Application ID")
    document_type: str = Field(..., description="Document type: passport, visa, work_permit, etc.")
    document_number: Optional[str] = Field(None, description="Document identification number")
    expiry_date: Optional[str] = Field(None, description="Document expiry date (YYYY-MM-DD)")


class EEOReportRequest(BaseModel):
    """Request model for EEO report generation."""
    start_date: str = Field(..., description="Report start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Report end date (YYYY-MM-DD)")
    job_id: Optional[int] = Field(None, description="Limit to specific job")


@router.post(
    "/adverse-action",
    summary="Generate Adverse Action Notice",
    description="Generate FCRA-compliant adverse action notice. Requires application:reject permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_REJECT))],
)
async def generate_adverse_action_notice(
    request: AdverseActionRequest,
    current_user: User = Depends(require_active_user),
):
    """Generate pre- or final adverse action notice with required consumer rights information."""
    if request.notice_type not in ["pre", "final"]:
        raise HTTPException(status_code=400, detail="Notice type must be 'pre' or 'final'")
    
    result = await compliance_service.generate_adverse_action_notice(
        application_id=request.application_id,
        reason=request.reason,
        notice_type=request.notice_type,
        generated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/work-authorization",
    summary="Verify Work Authorization",
    description="Initiate I-9/E-Verify work authorization check. Requires application:advance permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_ADVANCE))],
)
async def verify_work_authorization(
    request: WorkAuthorizationRequest,
    current_user: User = Depends(require_active_user),
):
    """Submit work authorization documents for I-9 and E-Verify verification."""
    result = await compliance_service.verify_work_authorization(
        application_id=request.application_id,
        document_type=request.document_type,
        document_number=request.document_number,
        expiry_date=request.expiry_date,
        verified_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "/export/{user_id}",
    summary="Export User Data (GDPR)",
    description="Export all data for a user (GDPR Article 15). Requires candidate:export permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_EXPORT))],
)
async def export_user_data(
    user_id: int = Path(..., description="User or candidate ID"),
    current_user: User = Depends(require_active_user),
):
    """Export complete user data for GDPR data subject access request."""
    result = await compliance_service.export_user_data(user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete(
    "/erase/{user_id}",
    summary="Erase User Data (GDPR)",
    description="Erase all user data (GDPR Article 17). Requires candidate:delete permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_DELETE))],
)
async def erase_user_data(
    user_id: int = Path(..., description="User or candidate ID"),
    current_user: User = Depends(require_active_user),
):
    """Permanently erase user data for GDPR right to be forgotten request."""
    result = await compliance_service.erase_user_data(
        user_id=user_id,
        erased_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post(
    "/eeo-report",
    summary="Generate EEO Report",
    description="Generate EEO-1 compliance report. Requires report:compliance permission.",
    dependencies=[Depends(require_permission(Permission.REPORT_COMPLIANCE))],
)
async def generate_eeo_report(
    request: EEOReportRequest,
    current_user: User = Depends(require_active_user),
):
    """Queue EEO-1 report generation for compliance reporting."""
    result = await compliance_service.generate_eeo_report(
        start_date=request.start_date,
        end_date=request.end_date,
        job_id=request.job_id,
        organization_id=current_user.organization_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
