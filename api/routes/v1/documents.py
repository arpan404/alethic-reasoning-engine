"""Document retrieval API routes."""

from fastapi import APIRouter, Depends, Path, HTTPException

from api.dependencies import require_active_user
from database.models.users import User
from api.services import documents as document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/resume/{application_id}")
async def get_resume(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get parsed resume data for an application."""
    result = await document_service.get_resume(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Resume not found")
    return result


@router.get("/cover-letter/{application_id}")
async def get_cover_letter(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get cover letter content for an application."""
    result = await document_service.get_cover_letter(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return result


@router.get("/linkedin/{application_id}")
async def get_linkedin_profile(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get LinkedIn profile data for an application."""
    result = await document_service.get_linkedin_profile(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="LinkedIn profile not found")
    return result


@router.get("/portfolio/{application_id}")
async def get_portfolio(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get portfolio items for an application."""
    result = await document_service.get_portfolio(application_id)
    return result


@router.get("/all/{application_id}")
async def get_all_documents(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get all documents for an application."""
    result = await document_service.get_all_documents(application_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
