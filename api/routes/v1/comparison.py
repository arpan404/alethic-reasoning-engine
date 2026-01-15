"""Comparison API routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import comparison as comparison_service

router = APIRouter(prefix="/comparison", tags=["comparison"])


class ComparisonRequest(BaseModel):
    application_ids: List[int] = Field(..., min_length=2, max_length=5)
    aspects: List[str] = Field(
        default=["skills", "experience", "education", "ai_scores"],
        description="Aspects to compare"
    )


@router.post("/side-by-side")
async def compare_candidates_side_by_side(
    request: ComparisonRequest,
    current_user: User = Depends(require_active_user),
):
    """
    Compare multiple candidates side-by-side.
    
    Returns a structured comparison across specified aspects
    with AI-generated insights.
    """
    if len(request.application_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 applications required for comparison"
        )
    
    result = await comparison_service.compare_candidates(
        application_ids=request.application_ids,
        aspects=request.aspects
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
