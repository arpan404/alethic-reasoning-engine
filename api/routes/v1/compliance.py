"""Compliance API routes (GDPR, FCRA, EEO)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import compliance as compliance_service

router = APIRouter(prefix="/compliance", tags=["compliance"])


class AdverseActionRequest(BaseModel):
    application_id: int
    reason: str = Field(..., min_length=10)
    notice_type: str = Field(default="pre", pattern="^(pre|final)$")


class WorkAuthorizationRequest(BaseModel):
    application_id: int
    document_type: str = Field(..., description="Document type (e.g., passport, visa)")
    document_number: Optional[str] = None
    expiry_date: Optional[str] = Field(None, description="Expiry date in YYYY-MM-DD format")


class EEOReportRequest(BaseModel):
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    job_id: Optional[int] = None


# FCRA Compliance Endpoints

@router.post("/adverse-action")
async def generate_adverse_action_notice(
    request: AdverseActionRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Generate FCRA-compliant adverse action notice.
    
    Creates either a pre-adverse action notice (5 business days wait)
    or a final adverse action notice.
    """
    result = await compliance_service.generate_adverse_action_notice(
        application_id=request.application_id,
        reason=request.reason,
        notice_type=request.notice_type,
        generated_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/work-authorization")
async def verify_work_authorization(
    request: WorkAuthorizationRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Verify I-9 work authorization for a candidate.
    
    Initiates verification process with E-Verify if applicable.
    """
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


# GDPR Data Rights Endpoints

@router.get("/data-export/{user_id}")
async def export_user_data(
    user_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """
    Export all data for a user (GDPR Article 15 - Right of Access).
    
    Returns all personal data stored about the user.
    """
    result = await compliance_service.export_user_data(user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.delete("/data-erasure/{user_id}")
async def erase_user_data(
    user_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """
    Erase all user data (GDPR Article 17 - Right to Erasure).
    
    This anonymizes the user's data. This action is irreversible.
    """
    result = await compliance_service.erase_user_data(
        user_id=user_id,
        erased_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to erase data"))
    
    return result


# EEO Reporting Endpoints

@router.post("/eeo-report")
async def generate_eeo_report(
    request: EEOReportRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Generate EEO (Equal Employment Opportunity) report.
    
    Creates a report for the specified date range.
    Returns a task ID for tracking progress.
    """
    result = await compliance_service.generate_eeo_report(
        start_date=request.start_date,
        end_date=request.end_date,
        job_id=request.job_id,
        organization_id=current_user.organization_id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result
