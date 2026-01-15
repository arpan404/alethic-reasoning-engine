"""
Candidate comparison endpoints.

Provides REST API for side-by-side candidate comparison with AI analysis.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import comparison as comparison_service

router = APIRouter(prefix="/compare", tags=["comparison"])


@router.get(
    "",
    summary="Compare Candidates",
    description="Compare multiple candidates side-by-side. Requires application:review permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_REVIEW))],
)
async def compare_candidates(
    application_ids: str = Query(
        ...,
        description="Comma-separated application IDs (2-5 candidates)",
        example="123,456,789"
    ),
    aspects: Optional[str] = Query(
        None,
        description="Comma-separated aspects to compare: skills,experience,education,ai_scores"
    ),
    current_user: User = Depends(require_active_user),
):
    """Compare 2-5 candidates across selected aspects with skill overlap analysis."""
    try:
        ids = [int(id.strip()) for id in application_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application ID format")
    
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 application IDs required")
    if len(ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 applications can be compared")
    
    aspect_list = None
    if aspects:
        aspect_list = [a.strip() for a in aspects.split(",")]
        valid_aspects = {"skills", "experience", "education", "ai_scores"}
        invalid = set(aspect_list) - valid_aspects
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid aspects: {invalid}. Valid: {valid_aspects}"
            )
    
    result = await comparison_service.compare_candidates(
        application_ids=ids,
        aspects=aspect_list,
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
