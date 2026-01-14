"""AI evaluation tools for Alethic agents.

These tools provide access to AI evaluation data and the ability
to trigger new evaluations via the task queue.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application, EvaluationPhase, EvaluationStatus
from database.models.ai_evaluations import (
    AIEvaluation,
    EvaluationType,
    AIScreeningResult,
    AIAssessmentResult,
)
from agents.tools.queue import enqueue_task

logger = logging.getLogger(__name__)


async def get_pre_evaluation(application_id: int) -> Optional[Dict[str, Any]]:
    """Get the pre-evaluation (light screening) results for an application.
    
    Pre-evaluation matches the resume against job description to evaluate:
    - Relevant experience
    - Required and transferable skills
    - Basic fit assessment
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary containing pre-evaluation results, or None if not available
    """
    async with AsyncSessionLocal() as session:
        # Get the screening evaluation
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.screening_result))
            .where(
                and_(
                    AIEvaluation.application_id == application_id,
                    AIEvaluation.evaluation_type == EvaluationType.SCREENING,
                )
            )
            .order_by(desc(AIEvaluation.created_at))
            .limit(1)
        )
        result = await session.execute(query)
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            return None
        
        screening = evaluation.screening_result
        
        return {
            "application_id": application_id,
            "evaluation_id": evaluation.id,
            "status": evaluation.status,
            "phase": "pre_evaluation",
            "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None,
            # Scores
            "overall_score": evaluation.overall_score,
            "match_score": screening.match_score if screening else None,
            "skills_score": screening.skills_score if screening else None,
            "experience_score": screening.experience_score if screening else None,
            "education_score": screening.education_score if screening else None,
            # Recommendation
            "recommendation": evaluation.recommendation,
            "recommendation_reason": evaluation.recommendation_reason,
            # Detailed analysis
            "matched_skills": screening.matched_skills if screening else [],
            "missing_skills": screening.missing_skills if screening else [],
            "transferable_skills": screening.transferable_skills if screening else [],
            "experience_summary": screening.experience_summary if screening else None,
            "strengths": screening.strengths if screening else [],
            "concerns": screening.concerns if screening else [],
            "summary": evaluation.summary,
        }


async def get_full_evaluation(application_id: int) -> Optional[Dict[str, Any]]:
    """Get the full evaluation (deep analysis) results for an application.
    
    Full evaluation includes deep analysis of:
    - Resume
    - Cover letter
    - LinkedIn profile
    - Portfolios or additional documents
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary containing full evaluation results, or None if not available
    """
    async with AsyncSessionLocal() as session:
        # Get comprehensive evaluation
        query = (
            select(AIEvaluation)
            .where(
                and_(
                    AIEvaluation.application_id == application_id,
                    AIEvaluation.evaluation_type == EvaluationType.ANALYSIS,
                )
            )
            .order_by(desc(AIEvaluation.created_at))
            .limit(1)
        )
        result = await session.execute(query)
        evaluation = result.scalar_one_or_none()
        
        if not evaluation:
            return None
        
        return {
            "application_id": application_id,
            "evaluation_id": evaluation.id,
            "status": evaluation.status,
            "phase": "full_evaluation",
            "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None,
            # Scores
            "overall_score": evaluation.overall_score,
            "role_fit_score": evaluation.role_fit_score,
            "experience_depth_score": evaluation.experience_depth_score,
            "growth_potential_score": evaluation.growth_potential_score,
            "culture_fit_score": evaluation.culture_fit_score,
            # Recommendation
            "recommendation": evaluation.recommendation,
            "recommendation_reason": evaluation.recommendation_reason,
            # Detailed analysis
            "summary": evaluation.summary,
            "detailed_analysis": evaluation.detailed_analysis,
            "strengths": evaluation.strengths or [],
            "concerns": evaluation.concerns or [],
            "interview_suggestions": evaluation.interview_suggestions or [],
            "documents_analyzed": evaluation.documents_analyzed or [],
        }


async def get_prescreening_results(application_id: int) -> List[Dict[str, Any]]:
    """Get AI prescreening (scenario-based evaluation) results.
    
    Prescreening includes:
    - Scenario-based, job-relevant evaluations
    - Problem-solving assessment
    - Communication evaluation
    - Role-specific skill testing
    
    Args:
        application_id: The application ID
        
    Returns:
        List of prescreening round results
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(AIEvaluation)
            .options(selectinload(AIEvaluation.assessment_result))
            .where(
                and_(
                    AIEvaluation.application_id == application_id,
                    AIEvaluation.evaluation_type == EvaluationType.ASSESSMENT,
                )
            )
            .order_by(AIEvaluation.created_at)
        )
        result = await session.execute(query)
        evaluations = result.scalars().all()
        
        results = []
        for i, evaluation in enumerate(evaluations, 1):
            assessment = evaluation.assessment_result
            
            results.append({
                "round": i,
                "evaluation_id": evaluation.id,
                "status": evaluation.status,
                "completed_at": evaluation.completed_at.isoformat() if evaluation.completed_at else None,
                # Scores
                "overall_score": evaluation.overall_score,
                "problem_solving_score": assessment.problem_solving_score if assessment else None,
                "communication_score": assessment.communication_score if assessment else None,
                "technical_score": assessment.technical_score if assessment else None,
                # Results
                "passed": assessment.passed if assessment else None,
                "summary": evaluation.summary,
                "scenario_type": assessment.scenario_type if assessment else None,
                "time_taken_seconds": assessment.time_taken_seconds if assessment else None,
                "questions_answered": assessment.questions_answered if assessment else 0,
                "feedback": assessment.feedback if assessment else None,
            })
        
        return results


async def trigger_pre_evaluation(
    application_id: int,
    priority: str = "normal",
    requested_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Trigger a pre-evaluation (light screening) for an application.
    
    Args:
        application_id: The application to evaluate
        priority: Queue priority (low, normal, high, urgent)
        requested_by: User ID requesting the evaluation
        
    Returns:
        Dictionary with task_id and status
    """
    # Verify application exists
    async with AsyncSessionLocal() as session:
        query = select(Application).where(Application.id == application_id)
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
        
        # Check if evaluation is already in progress
        eval_query = select(AIEvaluation).where(
            and_(
                AIEvaluation.application_id == application_id,
                AIEvaluation.evaluation_type == EvaluationType.SCREENING,
                AIEvaluation.status.in_(["queued", "in_progress"]),
            )
        )
        eval_result = await session.execute(eval_query)
        existing_eval = eval_result.scalar_one_or_none()
        
        if existing_eval:
            return {
                "success": False,
                "error": "Pre-evaluation is already in progress",
                "evaluation_id": existing_eval.id,
                "status": existing_eval.status,
            }
    
    # Queue the evaluation task
    task_result = await enqueue_task(
        task_type="pre_evaluation",
        payload={
            "application_id": application_id,
            "requested_by": requested_by,
        },
        priority=priority,
    )
    
    logger.info(f"Triggered pre-evaluation for application {application_id}")
    
    return {
        "success": True,
        "application_id": application_id,
        "task_id": task_result.get("task_id"),
        "message": "Pre-evaluation has been queued and will be processed shortly",
    }


async def trigger_full_evaluation(
    application_id: int,
    include_linkedin: bool = True,
    include_portfolio: bool = True,
    priority: str = "normal",
    requested_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Trigger a full evaluation (deep analysis) for an application.
    
    Args:
        application_id: The application to evaluate
        include_linkedin: Whether to analyze LinkedIn profile
        include_portfolio: Whether to analyze portfolio/additional documents
        priority: Queue priority (low, normal, high, urgent)
        requested_by: User ID requesting the evaluation
        
    Returns:
        Dictionary with task_id and status
    """
    # Verify application exists
    async with AsyncSessionLocal() as session:
        query = select(Application).where(Application.id == application_id)
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application with ID {application_id} not found",
            }
    
    # Queue the evaluation task
    task_result = await enqueue_task(
        task_type="full_evaluation",
        payload={
            "application_id": application_id,
            "include_linkedin": include_linkedin,
            "include_portfolio": include_portfolio,
            "requested_by": requested_by,
        },
        priority=priority,
    )
    
    logger.info(f"Triggered full evaluation for application {application_id}")
    
    return {
        "success": True,
        "application_id": application_id,
        "task_id": task_result.get("task_id"),
        "message": "Full evaluation has been queued and will be processed shortly",
    }


async def get_candidate_ranking(
    job_id: int,
    stage: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get ranked list of candidates for a job.
    
    Ranks candidates using combined signals from:
    - Pre-evaluation scores
    - Full evaluation scores
    - Prescreening performance
    
    Args:
        job_id: The job to get rankings for
        stage: Optional filter by current stage
        limit: Maximum number of candidates to return
        
    Returns:
        Dictionary with ranked candidates and scoring breakdown
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(
                and_(
                    Application.job_id == job_id,
                    Application.status != "rejected",
                    Application.ai_overall_score.isnot(None),
                )
            )
        )
        
        if stage:
            query = query.where(Application.current_stage == stage)
        
        # Order by overall score descending
        query = query.order_by(desc(Application.ai_overall_score)).limit(limit)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        rankings = []
        for rank, app in enumerate(applications, 1):
            candidate_name = ""
            if app.candidate:
                candidate_name = f"{app.candidate.first_name} {app.candidate.last_name}".strip()
            
            rankings.append({
                "rank": rank,
                "application_id": app.id,
                "candidate_id": app.candidate_id,
                "candidate_name": candidate_name,
                "current_stage": app.current_stage,
                "is_shortlisted": app.is_shortlisted,
                # Scores
                "overall_score": app.ai_overall_score,
                "match_score": app.ai_match_score,
                "skills_score": app.ai_skills_score,
                "experience_score": app.ai_experience_score,
                # Recommendation
                "recommendation": app.ai_recommendation,
                "summary": app.ai_summary,
            })
        
        return {
            "job_id": job_id,
            "total_ranked": len(rankings),
            "stage_filter": stage,
            "rankings": rankings,
        }
