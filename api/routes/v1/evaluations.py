"""AI Evaluation API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from api.dependencies import require_active_user
from database.models.users import User
from api.services import evaluations as evaluation_service

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class TriggerEvaluationRequest(BaseModel):
    evaluation_type: str = Field(
        default="pre",
        pattern="^(pre|full)$",
        description="Type of evaluation: 'pre' for quick screening, 'full' for deep analysis"
    )


@router.get("/pre/{application_id}")
async def get_pre_evaluation(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get pre-evaluation (quick screening) results for an application."""
    result = await evaluation_service.get_pre_evaluation(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pre-evaluation not found")
    return result


@router.get("/full/{application_id}")
async def get_full_evaluation(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get full evaluation (deep analysis) results for an application."""
    result = await evaluation_service.get_full_evaluation(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Full evaluation not found")
    return result


@router.get("/prescreening/{application_id}")
async def get_prescreening(
    application_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get AI prescreening (scenario-based evaluation) results."""
    result = await evaluation_service.get_prescreening(application_id)
    if not result:
        raise HTTPException(status_code=404, detail="Prescreening not found")
    return result


@router.post("/{application_id}/trigger")
async def trigger_evaluation(
    application_id: int = Path(...),
    request: TriggerEvaluationRequest = Body(default=TriggerEvaluationRequest()),
    current_user: User = Depends(require_active_user),
):
    """
    Trigger an AI evaluation for an application.
    
    Use 'pre' for quick screening or 'full' for deep analysis.
    """
    result = await evaluation_service.trigger_evaluation(
        application_id=application_id,
        evaluation_type=request.evaluation_type,
        requested_by=current_user.id,
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/rankings/{job_id}")
async def get_candidate_rankings(
    job_id: int = Path(...),
    stage: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_active_user),
):
    """Get AI-ranked list of candidates for a job."""
    result = await evaluation_service.get_candidate_rankings(
        job_id=job_id,
        stage=stage,
        limit=limit,
    )
    return result
