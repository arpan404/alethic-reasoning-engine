"""Candidate comparison tools for Alethic agents.

These tools provide structured data for comparing candidates side-by-side,
enabling the LLM to generate detailed comparison narratives.
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


async def compare_candidates_side_by_side(
    application_ids: List[int],
) -> Dict[str, Any]:
    """Get structured comparison data for multiple candidates.
    
    Returns comprehensive data about each candidate to enable
    the LLM to generate an informed comparison and recommendation.
    
    Args:
        application_ids: List of application IDs to compare (2-5)
        
    Returns:
        Dictionary with comparison data for each candidate
    """
    if len(application_ids) < 2:
        return {
            "success": False,
            "error": "At least 2 applications required for comparison",
        }
    
    if len(application_ids) > 5:
        return {
            "success": False,
            "error": "Maximum 5 applications can be compared at once",
        }
    
    async with AsyncSessionLocal() as session:
        # Get applications with full data
        query = (
            select(Application)
            .options(
                selectinload(Application.candidate).selectinload(Candidate.education),
                selectinload(Application.candidate).selectinload(Candidate.experience),
                selectinload(Application.job),
                selectinload(Application.evaluations),
            )
            .where(Application.id.in_(application_ids))
        )
        result = await session.execute(query)
        applications = result.scalars().all()
        
        if len(applications) != len(application_ids):
            found_ids = {a.id for a in applications}
            missing_ids = [aid for aid in application_ids if aid not in found_ids]
            return {
                "success": False,
                "error": f"Some applications not found: {missing_ids}",
            }
        
        # Get job info (should be same job for all)
        job_info = None
        job_ids = set()
        for app in applications:
            job_ids.add(app.job_id)
            if not job_info and app.job:
                job_info = {
                    "id": app.job.id,
                    "title": app.job.title,
                    "required_skills": app.job.required_skills or [],
                    "preferred_skills": app.job.preferred_skills or [],
                    "experience_min_years": app.job.experience_min_years,
                    "education_level": app.job.education_level,
                    "ideal_candidate_description": app.job.ideal_candidate_description,
                }
        
        # Build comparison data for each candidate
        candidates_data = []
        for app in applications:
            candidate = app.candidate
            if not candidate:
                continue
            
            # Get latest evaluations
            screening_eval = None
            analysis_eval = None
            for eval in (app.evaluations or []):
                if eval.evaluation_type == EvaluationType.SCREENING and not screening_eval:
                    screening_eval = eval
                elif eval.evaluation_type == EvaluationType.ANALYSIS and not analysis_eval:
                    analysis_eval = eval
            
            # Calculate total experience
            total_experience_months = 0
            for exp in (candidate.experience or []):
                if exp.start_date:
                    end = exp.end_date or app.created_at
                    if end:
                        months = ((end.year - exp.start_date.year) * 12 + 
                                  (end.month - exp.start_date.month))
                        total_experience_months += max(0, months)
            
            candidates_data.append({
                "application_id": app.id,
                "candidate_id": candidate.id,
                # Basic info
                "name": f"{candidate.first_name} {candidate.last_name}".strip(),
                "headline": candidate.headline,
                "location": candidate.location,
                # Experience
                "experience_level": candidate.experience_level,
                "years_of_experience": candidate.years_of_experience or (total_experience_months / 12),
                "current_role": (candidate.experience[0].title if candidate.experience else None),
                "current_company": (candidate.experience[0].company if candidate.experience else None),
                "past_companies": [exp.company for exp in (candidate.experience or [])[:5]],
                # Education
                "education_level": candidate.education_level,
                "highest_degree": (candidate.education[0].degree if candidate.education else None),
                "alma_mater": (candidate.education[0].institution if candidate.education else None),
                # Skills
                "skills": candidate.skills or [],
                "languages": candidate.languages or [],
                # Application info
                "current_stage": app.current_stage,
                "is_shortlisted": app.is_shortlisted,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                # AI Scores
                "scores": {
                    "overall": app.ai_overall_score,
                    "match": app.ai_match_score,
                    "skills": app.ai_skills_score,
                    "experience": app.ai_experience_score,
                },
                "recommendation": app.ai_recommendation,
                "summary": app.ai_summary,
                # Evaluation details
                "screening_evaluation": {
                    "strengths": screening_eval.strengths if screening_eval else [],
                    "concerns": screening_eval.concerns if screening_eval else [],
                } if screening_eval else None,
                "analysis_evaluation": {
                    "role_fit_score": analysis_eval.role_fit_score if analysis_eval else None,
                    "growth_potential_score": analysis_eval.growth_potential_score if analysis_eval else None,
                    "culture_fit_score": analysis_eval.culture_fit_score if analysis_eval else None,
                    "interview_suggestions": (analysis_eval.interview_suggestions or []) if analysis_eval else [],
                } if analysis_eval else None,
                # Salary
                "salary_expectation": {
                    "min": candidate.salary_expectation_min,
                    "max": candidate.salary_expectation_max,
                    "currency": candidate.salary_currency,
                },
            })
        
        # Sort by overall score
        candidates_data.sort(
            key=lambda x: x["scores"].get("overall") or 0,
            reverse=True
        )
        
        # Calculate comparison dimensions
        comparison_dimensions = {
            "experience_years": {
                c["name"]: c["years_of_experience"]
                for c in candidates_data
            },
            "overall_scores": {
                c["name"]: c["scores"].get("overall")
                for c in candidates_data
            },
            "skills_scores": {
                c["name"]: c["scores"].get("skills")
                for c in candidates_data
            },
            "recommendations": {
                c["name"]: c["recommendation"]
                for c in candidates_data
            },
        }
        
        # Find common and unique skills
        all_skills_sets = [set(c["skills"]) for c in candidates_data]
        common_skills = set.intersection(*all_skills_sets) if all_skills_sets else set()
        
        for c in candidates_data:
            c["unique_skills"] = list(set(c["skills"]) - common_skills)
        
        return {
            "success": True,
            "job": job_info,
            "comparing_same_job": len(job_ids) == 1,
            "candidate_count": len(candidates_data),
            "candidates": candidates_data,
            "comparison_dimensions": comparison_dimensions,
            "common_skills": list(common_skills),
        }
