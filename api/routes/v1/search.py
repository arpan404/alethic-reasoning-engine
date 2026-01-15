"""Search API routes."""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import search as search_service

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    job_id: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")


class SimilarCandidatesRequest(BaseModel):
    application_id: int
    limit: int = Field(default=10, ge=1, le=50)


@router.post("/candidates")
async def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Perform semantic search for candidates.
    
    Uses natural language to find matching candidates.
    """
    result = await search_service.semantic_search(
        query=request.query,
        job_id=request.job_id,
        limit=request.limit,
        filters=request.filters,
    )
    return result


@router.post("/similar")
async def find_similar_candidates(
    request: SimilarCandidatesRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Find candidates similar to a reference candidate.
    
    Uses embedding similarity to find matches.
    """
    result = await search_service.find_similar_candidates(
        application_id=request.application_id,
        limit=request.limit,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/match/{job_id}")
async def match_candidates_to_job(
    job_id: int = Path(...),
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.0, ge=0.0, le=100.0),
    current_user: User = Depends(require_active_user),
):
    """
    Find best matching candidates for a job.
    
    Returns candidates ranked by match score.
    """
    result = await search_service.match_candidates_to_job(
        job_id=job_id,
        limit=limit,
        min_score=min_score,
    )
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result
