"""Evaluation service functions."""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.ai_evaluations import AIEvaluation, EvaluationType, AIScreeningResult
from database.models.applications import Application
from database.models.candidates import Candidate

logger = logging.getLogger(__name__)


async def get_pre_evaluation(application_id: int) -> Optional[Dict[str, Any]]:
    """Get pre-evaluation results."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AIEvaluation)
            .where(
                AIEvaluation.application_id == application_id,
                AIEvaluation.evaluation_type == EvaluationType.PRE_EVALUATION,
            )
            .order_by(AIEvaluation.created_at.desc())
            .limit(1)
        )
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            return None
        
        return {
            "id": evaluation.id,
            "application_id": application_id,
            "evaluation_type": "pre",
            "status": evaluation.status,
            "overall_score": evaluation.overall_score,
            "skills_match_score": evaluation.skills_match_score,
            "experience_match_score": evaluation.experience_match_score,
            "recommendation": evaluation.recommendation,
            "summary": evaluation.summary,
            "strengths": evaluation.strengths or [],
            "concerns": evaluation.concerns or [],
            "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        }


async def get_full_evaluation(application_id: int) -> Optional[Dict[str, Any]]:
    """Get full evaluation results."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AIEvaluation)
            .where(
                AIEvaluation.application_id == application_id,
                AIEvaluation.evaluation_type == EvaluationType.FULL_EVALUATION,
            )
            .order_by(AIEvaluation.created_at.desc())
            .limit(1)
        )
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            return None
        
        return {
            "id": evaluation.id,
            "application_id": application_id,
            "evaluation_type": "full",
            "status": evaluation.status,
            "overall_score": evaluation.overall_score,
            "skills_match_score": evaluation.skills_match_score,
            "experience_match_score": evaluation.experience_match_score,
            "culture_fit_score": evaluation.culture_fit_score if hasattr(evaluation, 'culture_fit_score') else None,
            "growth_potential_score": evaluation.growth_potential_score if hasattr(evaluation, 'growth_potential_score') else None,
            "recommendation": evaluation.recommendation,
            "detailed_analysis": evaluation.detailed_analysis if hasattr(evaluation, 'detailed_analysis') else None,
            "summary": evaluation.summary,
            "strengths": evaluation.strengths or [],
            "concerns": evaluation.concerns or [],
            "interview_focus_areas": evaluation.interview_focus_areas if hasattr(evaluation, 'interview_focus_areas') else [],
            "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        }


async def get_prescreening(application_id: int) -> Optional[Dict[str, Any]]:
    """Get AI prescreening results."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AIScreeningResult)
            .where(AIScreeningResult.application_id == application_id)
            .order_by(AIScreeningResult.created_at.desc())
        )
        screenings = result.scalars().all()
        
        if not screenings:
            return None
        
        rounds = []
        for screening in screenings:
            rounds.append({
                "id": screening.id,
                "round_number": screening.round_number if hasattr(screening, 'round_number') else 1,
                "status": screening.status,
                "score": screening.score,
                "passed": screening.passed if hasattr(screening, 'passed') else None,
                "feedback": screening.feedback if hasattr(screening, 'feedback') else None,
                "created_at": screening.created_at.isoformat() if screening.created_at else None,
            })
        
        return {
            "application_id": application_id,
            "total_rounds": len(rounds),
            "rounds": rounds,
        }


async def trigger_evaluation(
    application_id: int,
    evaluation_type: str = "pre",
    requested_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Trigger an AI evaluation."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application).where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"success": False, "error": "Application not found"}
    
    try:
        from workers.tasks import queue_evaluation
        task_id = await queue_evaluation(
            application_id=application_id,
            evaluation_type=evaluation_type,
            requested_by=requested_by,
        )
        return {
            "success": True,
            "task_id": task_id,
            "application_id": application_id,
            "evaluation_type": evaluation_type,
            "status": "queued",
        }
    except Exception as e:
        logger.error(f"Failed to queue evaluation: {e}")
        return {"success": False, "error": "Failed to queue evaluation"}


async def get_candidate_rankings(
    job_id: int,
    stage: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get ranked candidates for a job."""
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(
                Application.job_id == job_id,
                Application.ai_overall_score.isnot(None),
            )
        )
        
        if stage:
            query = query.where(Application.current_stage == stage)
        
        query = query.order_by(Application.ai_overall_score.desc())
        query = query.limit(limit)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        rankings = []
        for rank, app in enumerate(applications, 1):
            candidate = app.candidate
            rankings.append({
                "rank": rank,
                "application_id": app.id,
                "candidate_id": candidate.id if candidate else None,
                "candidate_name": f"{candidate.first_name} {candidate.last_name}" if candidate else None,
                "overall_score": app.ai_overall_score,
                "recommendation": app.ai_recommendation,
                "stage": app.current_stage,
                "is_shortlisted": app.is_shortlisted,
            })
        
        return {
            "job_id": job_id,
            "rankings": rankings,
            "total_ranked": len(rankings),
        }
