"""Candidate management API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db, require_active_user
from api.schemas.common import PaginatedResponse, PaginationParams
from api.schemas.candidates import (
    CandidateCreate,
    CandidateUpdate,
    CandidateResponse,
)
from database.models.users import User
# from core.parsers.resume import parse_resume  # TODO: Implement
from workers.tasks.embeddings import generate_resume_embedding


router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("", response_model=PaginatedResponse[CandidateResponse])
async def list_candidates(
    pagination: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """List all candidates with pagination and optional search."""
    # TODO: Implement listing with filters
    return PaginatedResponse.create(
        items=[],
        total=0,
        pagination=pagination,
    )


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate: CandidateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Create a new candidate."""
    # TODO: Implement candidate creation
    # TODO: Trigger resume parsing if resume is provided
    
    if candidate.resume_url:
        # Queue resume parsing task
        parse_resume.delay(
            file_path=candidate.resume_url,
            candidate_id="",  # Will be set after creation
            organization_id=str(current_user.organization_id),
        )
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Get candidate by ID."""
    # TODO: Implement get candidate
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Candidate {candidate_id} not found",
    )


@router.patch("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    update_data: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Update candidate information."""
    # TODO: Implement update
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Delete candidate."""
    # TODO: Implement soft delete
    pass


@router.post("/{candidate_id}/parse-resume")
async def trigger_resume_parse(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    """Manually trigger resume parsing for a candidate."""
    # TODO: Fetch candidate and resume file path
    
    task = parse_resume.delay(
        file_path="",  # TODO: Get from database
        candidate_id=candidate_id,
        organization_id=str(current_user.organization_id),
    )
    
    return {
        "status": "queued",
        "task_id": task.id,
    }
