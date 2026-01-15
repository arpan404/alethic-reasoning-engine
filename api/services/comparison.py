"""
Comparison service functions for API endpoints.

Provides direct database operations for candidate comparison,
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application
from database.models.candidates import Candidate
from database.models.ai_evaluations import AIEvaluation, EvaluationType

logger = logging.getLogger(__name__)


async def compare_candidates(
    application_ids: List[int],
    aspects: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compare multiple candidates side-by-side.
    
    Args:
        application_ids: List of application IDs to compare (2-5)
        aspects: Aspects to compare (skills, experience, education, ai_scores)
        
    Returns:
        Dictionary with comparison data
    """
    if len(application_ids) < 2:
        return {"error": "At least 2 applications required for comparison"}
    if len(application_ids) > 5:
        return {"error": "Maximum 5 applications can be compared"}
    
    aspects = aspects or ["skills", "experience", "education", "ai_scores"]
    
    async with AsyncSessionLocal() as session:
        # Fetch all applications with candidates
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id.in_(application_ids))
        )
        applications = result.scalars().all()
        
        if len(applications) < 2:
            return {"error": "Could not find enough valid applications"}
        
        # Build comparison data
        candidates_data = []
        all_skills = set()
        
        for app in applications:
            if not app.candidate:
                continue
                
            c = app.candidate
            candidate_info = {
                "application_id": app.id,
                "candidate_id": c.id,
                "name": f"{c.first_name} {c.last_name}",
                "current_title": c.current_title,
                "current_company": c.current_company,
            }
            
            if "skills" in aspects:
                candidate_info["skills"] = c.skills or []
                all_skills.update(c.skills or [])
            
            if "experience" in aspects:
                candidate_info["experience"] = {
                    "years": c.experience_years,
                    "work_history": c.work_history or [],
                }
            
            if "education" in aspects:
                candidate_info["education"] = c.education or []
            
            if "ai_scores" in aspects:
                candidate_info["ai_scores"] = {
                    "overall": app.ai_overall_score,
                    "recommendation": app.ai_recommendation,
                }
                
                # Try to get detailed evaluation
                eval_result = await session.execute(
                    select(AIEvaluation)
                    .where(
                        AIEvaluation.application_id == app.id,
                        AIEvaluation.evaluation_type == EvaluationType.FULL_EVALUATION,
                    )
                    .order_by(AIEvaluation.created_at.desc())
                    .limit(1)
                )
                evaluation = eval_result.scalar_one_or_none()
                
                if evaluation:
                    candidate_info["ai_scores"]["skills_match"] = evaluation.skills_match_score
                    candidate_info["ai_scores"]["experience_match"] = evaluation.experience_match_score
                    candidate_info["ai_scores"]["strengths"] = evaluation.strengths or []
                    candidate_info["ai_scores"]["concerns"] = evaluation.concerns or []
            
            candidates_data.append(candidate_info)
        
        # Calculate comparison insights
        comparison = {
            "candidates": candidates_data,
            "comparison_aspects": aspects,
            "total_compared": len(candidates_data),
        }
        
        if "skills" in aspects:
            # Find common and unique skills
            if len(candidates_data) >= 2:
                skill_sets = [set(c.get("skills", [])) for c in candidates_data]
                common_skills = skill_sets[0]
                for s in skill_sets[1:]:
                    common_skills = common_skills & s
                
                comparison["common_skills"] = list(common_skills)
                
                # Unique skills per candidate
                for i, c in enumerate(candidates_data):
                    other_skills = set()
                    for j, other in enumerate(candidates_data):
                        if i != j:
                            other_skills.update(other.get("skills", []))
                    c["unique_skills"] = list(set(c.get("skills", [])) - other_skills)
        
        if "ai_scores" in aspects:
            # Rank by AI score
            ranked = sorted(
                candidates_data,
                key=lambda x: x.get("ai_scores", {}).get("overall") or 0,
                reverse=True
            )
            comparison["ranking"] = [
                {
                    "rank": i + 1,
                    "application_id": c["application_id"],
                    "name": c["name"],
                    "score": c.get("ai_scores", {}).get("overall"),
                }
                for i, c in enumerate(ranked)
            ]
        
        return comparison
