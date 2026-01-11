"""Tools for evaluation agent."""

from typing import Dict, Any, List


def calculate_technical_score(
    candidate_skills: List[str],
    required_skills: List[str],
    skill_weights: Dict[str, float] = None,
) -> float:
    """Calculate weighted technical skills score.
    
    Args:
        candidate_skills: List of candidate's skills
        required_skills: List of required skills for the job
        skill_weights: Optional weights for each skill
        
    Returns:
        Technical score between 0 and 100
    """
    if not required_skills:
        return 100.0
    
    if skill_weights is None:
        skill_weights = {skill: 1.0 for skill in required_skills}
    
    candidate_set = set(s.lower() for s in candidate_skills)
    matched_score = 0.0
    total_weight = 0.0
    
    for skill in required_skills:
        weight = skill_weights.get(skill, 1.0)
        total_weight += weight
        
        if skill.lower() in candidate_set:
            matched_score += weight
    
    return (matched_score / total_weight * 100) if total_weight > 0 else 0.0


def assess_cultural_fit(
    candidate_values: List[str],
    company_values: List[str],
    candidate_work_style: str,
    team_work_style: str,
) -> Dict[str, Any]:
    """Assess cultural fit between candidate and company.
    
    Args:
        candidate_values: Candidate's stated values
        company_values: Company's core values
        candidate_work_style: Description of candidate's work style
        team_work_style: Description of team's work style
        
    Returns:
        Cultural fit assessment with score and details
    """
    # Simple overlap calculation
    candidate_set = set(v.lower() for v in candidate_values)
    company_set = set(v.lower() for v in company_values)
    
    value_match = len(candidate_set.intersection(company_set)) / len(company_set) if company_set else 0
    
    # Work style compatibility (simplified)
    style_keywords = ["collaborative", "independent", "structured", "flexible", "fast-paced", "deliberate"]
    candidate_style_lower = candidate_work_style.lower()
    team_style_lower = team_work_style.lower()
    
    style_alignment = sum(
        1 for keyword in style_keywords 
        if keyword in candidate_style_lower and keyword in team_style_lower
    ) / len(style_keywords)
    
    # Combined score
    fit_score = (value_match * 0.6 + style_alignment * 0.4) * 100
    
    return {
        "fit_score": fit_score,
        "value_alignment": value_match * 100,
        "style_alignment": style_alignment * 100,
        "matched_values": list(candidate_set.intersection(company_set)),
        "recommendation": "Strong Fit" if fit_score >= 75 else "Moderate Fit" if fit_score >= 50 else "Needs Assessment",
    }


def predict_success_likelihood(
    technical_score: float,
    experience_score: float,
    cultural_fit_score: float,
    growth_potential_score: float,
) -> Dict[str, Any]:
    """Predict likelihood of candidate success.
    
    Args:
        technical_score: Technical skills score (0-100)
        experience_score: Experience match score (0-100)
        cultural_fit_score: Cultural fit score (0-100)
        growth_potential_score: Growth potential score (0-100)
        
    Returns:
        Success prediction with probability and risk factors
    """
    # Weighted average
    weights = {
        "technical": 0.35,
        "experience": 0.30,
        "cultural_fit": 0.20,
        "growth_potential": 0.15,
    }
    
    overall_score = (
        technical_score * weights["technical"] +
        experience_score * weights["experience"] +
        cultural_fit_score * weights["cultural_fit"] +
        growth_potential_score * weights["growth_potential"]
    )
    
    # Calculate success probability
    success_probability = overall_score / 100
    
    # Identify risk factors
    risk_factors = []
    if technical_score < 70:
        risk_factors.append("Technical skills below threshold")
    if experience_score < 60:
        risk_factors.append("Limited relevant experience")
    if cultural_fit_score < 50:
        risk_factors.append("Cultural fit concerns")
    if growth_potential_score < 50:
        risk_factors.append("Limited growth trajectory")
    
    # Retention prediction
    retention_score = (cultural_fit_score * 0.4 + growth_potential_score * 0.3 + 
                      experience_score * 0.3)
    
    return {
        "overall_score": overall_score,
        "success_probability": success_probability,
        "confidence_level": "High" if min(technical_score, experience_score) > 70 else "Medium" if min(technical_score, experience_score) > 50 else "Low",
        "risk_factors": risk_factors,
        "retention_prediction": "High" if retention_score >= 75 else "Moderate" if retention_score >= 50 else "At Risk",
        "recommendation": "Strongly Recommended" if overall_score >= 85 else "Recommended" if overall_score >= 70 else "Conditional" if overall_score >= 60 else "Not Recommended",
    }


def benchmark_against_peers(
    candidate_score: float,
    peer_scores: List[float],
) -> Dict[str, Any]:
    """Benchmark candidate against peer group.
    
    Args:
        candidate_score: Candidate's overall score
        peer_scores: List of scores from similar candidates
        
    Returns:
        Benchmarking analysis
    """
    if not peer_scores:
        return {"percentile": None, "ranking": "Unable to benchmark"}
    
    peer_scores_sorted = sorted(peer_scores)
    percentile = sum(1 for score in peer_scores if score < candidate_score) / len(peer_scores) * 100
    
    return {
        "candidate_score": candidate_score,
        "peer_average": sum(peer_scores) / len(peer_scores),
        "peer_median": peer_scores_sorted[len(peer_scores) // 2],
        "percentile": percentile,
        "ranking": "Top 10%" if percentile >= 90 else "Top 25%" if percentile >= 75 else "Above Average" if percentile >= 60 else "Average" if percentile >= 40 else "Below Average",
        "total_candidates": len(peer_scores),
    }
