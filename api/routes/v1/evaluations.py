"""
AI evaluation and ranking endpoints.

Provides REST API for accessing AI-generated candidate evaluations and rankings.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import evaluations as evaluation_service

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class TriggerEvaluationRequest(BaseModel):
    """Request model for triggering an evaluation."""
    evaluation_type: str = Field("pre", description="Type: 'pre' or 'full'")


@router.get(
    "/{application_id}/pre",
    summary="Get Pre-Evaluation",
    description="Get AI pre-evaluation results for quick screening. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_pre_evaluation(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve AI pre-evaluation with initial scores and screening results."""
    result = await evaluation_service.get_pre_evaluation(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pre-evaluation not found")
    return result


@router.get(
    "/{application_id}/full",
    summary="Get Full Evaluation",
    description="Get comprehensive AI evaluation results. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_full_evaluation(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve comprehensive AI evaluation with detailed analysis and interview focus areas."""
    result = await evaluation_service.get_full_evaluation(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Full evaluation not found")
    return result


@router.get(
    "/{application_id}/prescreening",
    summary="Get AI Prescreening",
    description="Get AI prescreening round results. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_prescreening(
    application_id: int = Path(..., description="Application ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve AI prescreening results showing pass/fail status and feedback."""
    result = await evaluation_service.get_prescreening(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prescreening not found")
    return result


@router.post(
    "/{application_id}/trigger",
    summary="Trigger Evaluation",
    description="Trigger a new AI evaluation. Requires application:review permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_REVIEW))],
)
async def trigger_evaluation(
    application_id: int = Path(..., description="Application ID"),
    request: TriggerEvaluationRequest = Body(default=TriggerEvaluationRequest()),
    current_user: User = Depends(require_active_user),
):
    """Queue a new AI evaluation for an application. Results available via GET endpoints."""
    result = await evaluation_service.trigger_evaluation(
        application_id=application_id,
        evaluation_type=request.evaluation_type,
        requested_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get(
    "/rankings",
    summary="Get Candidate Rankings",
    description="Get AI-ranked candidates for a job. Requires application:read permission.",
    dependencies=[Depends(require_permission(Permission.APPLICATION_READ))],
)
async def get_candidate_rankings(
    job_id: int = Query(..., description="Job ID"),
    stage: Optional[str] = Query(None, description="Filter by pipeline stage"),
    limit: int = Query(10, ge=1, le=50, description="Number of top candidates"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve candidates ranked by AI score for a specific job."""
    return await evaluation_service.get_candidate_rankings(
        job_id=job_id,
        stage=stage,
        limit=limit,
    )
