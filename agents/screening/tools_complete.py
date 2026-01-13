"""Comprehensive candidate screening and evaluation tools."""

from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import logging

from agents.common.utils_extended import weighted_average, normalize_score

logger = logging.getLogger(__name__)


def calculate_fit_score(
    candidate_profile: Dict[str, Any],
    job_requirements: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Calculate candidate fit score for a job.
    
    Args:
        candidate_profile: Candidate information
        job_requirements: Job requirements
        weights: Optional weights for different criteria
        
    Returns:
        Dictionary with overall score and breakdown
    """
    if weights is None:
        weights = {
            "skills": 0.35,
            "experience": 0.30,
            "education": 0.20,
            "location": 0.10,
            "salary": 0.05,
        }
    
    scores = {}
    
    # Skills match
    candidate_skills = set(s.lower() for s in candidate_profile.get("skills", []))
    required_skills = set(s.lower() for s in job_requirements.get("required_skills", []))
    preferred_skills = set(s.lower() for s in job_requirements.get("preferred_skills", []))
    
    if required_skills:
        required_match = len(candidate_skills.intersection(required_skills)) / len(required_skills)
        preferred_match = len(candidate_skills.intersection(preferred_skills)) / len(preferred_skills) if preferred_skills else 0
        scores["skills"] = (required_match * 0.7 + preferred_match * 0.3) * 100
    else:
        scores["skills"] = 50.0
    
    # Experience match
    candidate_years = candidate_profile.get("years_of_experience", 0)
    required_years = job_requirements.get("years_of_experience", 0)
    
    if required_years > 0:
        if candidate_years >= required_years:
            extra_years = candidate_years - required_years
            scores["experience"] = min(100, 100 + (extra_years * 2))
        else:
            scores["experience"] = (candidate_years / required_years) * 80
    else:
        scores["experience"] = 100.0
    
    # Education match
    candidate_degree = candidate_profile.get("education", {}).get("degree", "").lower()
    required_degree = job_requirements.get("education_level", "").lower()
    
    degree_hierarchy = {"high school": 1, "associate": 2, "bachelor": 3, "master": 4, "phd": 5}
    
    candidate_level = next((lvl for deg, lvl in degree_hierarchy.items() if deg in candidate_degree), 0)
    required_level = next((lvl for deg, lvl in degree_hierarchy.items() if deg in required_degree), 0)
    
    if required_level > 0:
        scores["education"] = 100.0 if candidate_level >= required_level else (candidate_level / required_level) * 60
    else:
        scores["education"] = 100.0
    
    # Location match
    candidate_location = candidate_profile.get("location", "").lower()
    preferred_location = job_requirements.get("location", "").lower()
    remote_ok = job_requirements.get("remote_ok", False)
    
    if remote_ok or not preferred_location:
        scores["location"] = 100.0
    elif candidate_location and preferred_location:
        scores["location"] = 100.0 if (candidate_location in preferred_location or preferred_location in candidate_location) else 50.0
    else:
        scores["location"] = 50.0
    
    # Salary match
    candidate_salary = candidate_profile.get("expected_salary", 0)
    job_salary_min = job_requirements.get("salary_min", 0)
    job_salary_max = job_requirements.get("salary_max", 0)
    
    if all([job_salary_min, job_salary_max, candidate_salary]):
        if job_salary_min <= candidate_salary <= job_salary_max:
            scores["salary"] = 100.0
        elif candidate_salary < job_salary_min:
            scores["salary"] = 80.0
        else:
            overage = (candidate_salary - job_salary_max) / job_salary_max
            scores["salary"] = max(0, 100 - (overage * 100))
    else:
        scores["salary"] = 100.0
    
    overall_score = weighted_average([scores.get(k, 0) for k in weights.keys()], [weights[k] for k in weights.keys()])
    
    return {
        "overall_score": round(overall_score, 2),
        "breakdown": scores,
        "weights": weights,
        "recommendation": _get_recommendation(overall_score),
    }


def rank_candidates(
    candidates: List[Dict[str, Any]],
    job_requirements: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Rank candidates for a job.
    
    Args:
        candidates: List of candidate profiles
        job_requirements: Job requirements
        weights: Optional weights for scoring
        
    Returns:
        Ranked list of candidates with scores
    """
    ranked = []
    for candidate in candidates:
        score_result = calculate_fit_score(candidate, job_requirements, weights)
        ranked.append({
            **candidate,
            "fit_score": score_result["overall_score"],
            "score_breakdown": score_result["breakdown"],
            "recommendation": score_result["recommendation"],
        })
    ranked.sort(key=lambda x: x["fit_score"], reverse=True)
    return ranked


def generate_screening_report(
    candidate_profile: Dict[str, Any],
    job_requirements: Dict[str, Any],
) -> Dict[str, Any]:
    """Create comprehensive screening report.
    
    Args:
        candidate_profile: Candidate information
        job_requirements: Job requirements
        
    Returns:
        Screening report
    """
    fit_score = calculate_fit_score(candidate_profile, job_requirements)
    
    return {
        "candidate_id": candidate_profile.get("id"),
        "candidate_name": candidate_profile.get("name"),
        "job_id": job_requirements.get("id"),
        "job_title": job_requirements.get("title"),
        "overall_fit_score": fit_score["overall_score"],
        "score_breakdown": fit_score["breakdown"],
        "recommendation": fit_score["recommendation"],
        "next_steps": _generate_next_steps(fit_score["overall_score"]),
    }


def _get_recommendation(score: float) -> str:
    """Get recommendation based on score."""
    if score >= 80:
        return "Strong Match - Highly Recommended"
    elif score >= 65:
        return "Good Match - Recommended"
    elif score >= 50:
        return "Moderate Match - Consider with Caution"
    else:
        return "Weak Match - Not Recommended"


def _generate_next_steps(score: float) -> str:
    """Generate next steps based on score."""
    if score >= 80:
        return "Schedule interview immediately. Prioritize this candidate."
    elif score >= 65:
        return "Schedule phone screen to assess fit further."
    elif score >= 50:
        return "Review application in detail before proceeding."
    else:
        return "Send rejection or keep in talent pool for future opportunities."
