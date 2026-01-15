"""
Document retrieval endpoints.

Provides REST API for accessing candidate resumes, cover letters, and portfolios.
Contains PII - access is logged for compliance.
"""

from fastapi import APIRouter, Depends, HTTPException, Path

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import documents as document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "/{application_id}/resume",
    summary="Get Resume",
    description="Get parsed resume for an application. Requires candidate:read permission. Contains PII.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_resume(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve parsed resume with contact info, experience, education, and skills."""
    result = await document_service.get_resume(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Resume not found")
    return result


@router.get(
    "/{application_id}/cover-letter",
    summary="Get Cover Letter",
    description="Get cover letter content for an application. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_cover_letter(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve cover letter text content if available."""
    result = await document_service.get_cover_letter(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.get(
    "/{application_id}/linkedin",
    summary="Get LinkedIn Profile",
    description="Get LinkedIn profile data for a candidate. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_linkedin_profile(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve LinkedIn profile data if available."""
    result = await document_service.get_linkedin_profile(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.get(
    "/{application_id}/portfolio",
    summary="Get Portfolio",
    description="Get portfolio items for a candidate. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_portfolio(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve portfolio files and URLs for a candidate."""
    result = await document_service.get_portfolio(application_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get(
    "/{application_id}",
    summary="Get All Documents",
    description="Get all documents for an application. Requires candidate:read permission. Contains PII.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def get_all_documents(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve all documents (resume, cover letters, portfolios) for an application."""
    result = await document_service.get_all_documents(application_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
