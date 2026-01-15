"""
Semantic search endpoints.

Provides REST API for AI-powered candidate search with semantic matching.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get(
    "",
    summary="Semantic Search",
    description="Search candidates using natural language queries. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def semantic_search(
    q: str = Query(..., min_length=2, description="Natural language search query"),
    job_id: Optional[int] = Query(None, description="Limit search to specific job"),
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum AI score"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    current_user: User = Depends(require_active_user),
):
    """Search for candidates using semantic matching against experience, skills, and background."""
    filters = {}
    if stage:
        filters["stage"] = stage
    if min_score:
        filters["min_score"] = min_score
    
    return await search_service.semantic_search(
        query=q,
        job_id=job_id,
        limit=limit,
        filters=filters if filters else None,
    )


@router.get(
    "/similar/{application_id}",
    summary="Find Similar Candidates",
    description="Find candidates similar to a reference candidate. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def find_similar_candidates(
    application_id: int = Path(..., description="Reference application ID"),
    limit: int = Query(10, ge=1, le=20, description="Maximum results"),
    current_user: User = Depends(require_active_user),
):
    """Find candidates with similar skills, experience, and background to a reference."""
    result = await search_service.find_similar_candidates(
        application_id=application_id,
        limit=limit,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get(
    "/match",
    summary="Match Candidates to Job",
    description="Find best matching candidates for a job. Requires candidate:read permission.",
    dependencies=[Depends(require_permission(Permission.CANDIDATE_READ))],
)
async def match_candidates_to_job(
    job_id: int = Query(..., description="Job ID to match against"),
    min_score: float = Query(0, ge=0, le=100, description="Minimum match score"),
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
    current_user: User = Depends(require_active_user),
):
    """Find candidates that best match job requirements ordered by AI score."""
    result = await search_service.match_candidates_to_job(
        job_id=job_id,
        limit=limit,
        min_score=min_score,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
