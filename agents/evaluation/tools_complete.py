"""Interview evaluation and assessment tools."""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def evaluate_interview_response(
    question: str,
    response: str,
    evaluation_criteria: List[str],
    scoring_rubric: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """Evaluate a candidate's interview response.
    
    Args:
        question: Interview question asked
        response: Candidate's response
        evaluation_criteria: List of criteria to evaluate
        scoring_rubric: Optional rubric with max points per criterion
        
    Returns:
        Evaluation result with scores and feedback
    """
    if scoring_rubric is None:
        scoring_rubric = {criterion: 10 for criterion in evaluation_criteria}
    
    scores = {}
    feedback = []
    
    response_length = len(response.split())
    
    for criterion in evaluation_criteria:
        # Simple heuristic scoring (in production, would use LLM)
        if criterion.lower() == "completeness":
            score = min(scoring_rubric[criterion], max(1, response_length // 20))
            feedback.append(f"Response length: {response_length} words")
        
        elif criterion.lower() == "relevance":
            # Check if response contains question keywords
            question_words = set(question.lower().split())
            response_words = set(response.lower().split())
            overlap = len(question_words.intersection(response_words))
            score = min(scoring_rubric[criterion], overlap)
            feedback.append(f"Keyword overlap: {overlap} words")
        
        elif criterion.lower() == "clarity":
            # Simple clarity check based on sentence structure
            sentences = response.split('.')
            score = min(scoring_rubric[criterion], len(sentences))
            feedback.append(f"Number of sentences: {len(sentences)}")
        
        else:
            score = scoring_rubric[criterion] // 2  # Default to middle score
        
        scores[criterion] = score
    
    total_score = sum(scores.values())
    max_score = sum(scoring_rubric.values())
    
    return {
        "question": question,
        "scores": scores,
        "total_score": total_score,
        "max_score": max_score,
        "percentage": round((total_score / max_score * 100) if max_score > 0 else 0, 2),
        "feedback": feedback,
    }


def score_technical_assessment(
    test_results: Dict[str, Any],
    passing_criteria: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Score technical assessment results.
    
    Args:
        test_results: Dictionary with test results
        passing_criteria: Optional passing thresholds
        
    Returns:
        Scoring result
    """
    if passing_criteria is None:
        passing_criteria = {
            "accuracy": 70.0,
            "time_efficiency": 60.0,
            "code_quality": 70.0,
        }
    
    scores = test_results.get("scores", {})
    passed_all = True
    failures = []
    
    for criterion, threshold in passing_criteria.items():
        score = scores.get(criterion, 0)
        if score < threshold:
            passed_all = False
            failures.append(f"{criterion}: {score}% (required: {threshold}%)")
    
    return {
        "passed": passed_all,
        "scores": scores,
        "passing_criteria": passing_criteria,
        "failures": failures,
        "overall_score": sum(scores.values()) / len(scores) if scores else 0,
    }


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
        candidate_work_style: Candidate's preferred work style
        team_work_style: Team's work style
        
    Returns:
        Cultural fit assessment
    """
    # Values alignment
    candidate_values_set = set(v.lower() for v in candidate_values)
    company_values_set = set(v.lower() for v in company_values)
    
    matched_values = candidate_values_set.intersection(company_values_set)
    values_score = (len(matched_values) / len(company_values) * 100) if company_values else 0
    
    # Work style compatibility
    work_style_compatible = candidate_work_style.lower() == team_work_style.lower()
    work_style_score = 100.0 if work_style_compatible else 50.0
    
    # Overall fit
    overall_fit = (values_score * 0.6 + work_style_score * 0.4)
    
    return {
        "values_alignment_score": round(values_score, 2),
        "matched_values": list(matched_values),
        "work_style_compatibility": work_style_compatible,
        "work_style_score": work_style_score,
        "overall_cultural_fit": round(overall_fit, 2),
        "recommendation": "Strong fit" if overall_fit >= 75 else "Moderate fit" if overall_fit >= 50 else "Weak fit",
    }


def generate_evaluation_summary(
    interview_scores: List[Dict[str, Any]],
    technical_scores: Optional[Dict[str, Any]] = None,
    cultural_fit: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate comprehensive evaluation summary.
    
    Args:
        interview_scores: List of interview evaluation results
        technical_scores: Optional technical assessment scores
        cultural_fit: Optional cultural fit assessment
        
    Returns:
        Evaluation summary
    """
    # Average interview scores
    avg_interview_score = 0
    if interview_scores:
        total_percentage = sum(score.get("percentage", 0) for score in interview_scores)
        avg_interview_score = total_percentage / len(interview_scores)
    
    # Technical score
    technical_score = 0
    if technical_scores:
        technical_score = technical_scores.get("overall_score", 0)
    
    # Cultural fit score
    cultural_score = 0
    if cultural_fit:
        cultural_score = cultural_fit.get("overall_cultural_fit", 0)
    
    # Calculate weighted overall score
    weights = {"interview": 0.40, "technical": 0.40, "cultural": 0.20}
    overall_score = (
        avg_interview_score * weights["interview"] +
        technical_score * weights["technical"] +
        cultural_score * weights["cultural"]
    )
    
    # Determine recommendation
    if overall_score >= 80:
        recommendation = "Strong Hire"
    elif overall_score >= 70:
        recommendation = "Hire"
    elif overall_score >= 60:
        recommendation = "Borderline - Further Review Needed"
    else:
        recommendation = "No Hire"
    
    return {
        "overall_score": round(overall_score, 2),
        "interview_score": round(avg_interview_score, 2),
        "technical_score": round(technical_score, 2),
        "cultural_fit_score": round(cultural_score, 2),
        "recommendation": recommendation,
        "weights": weights,
        "evaluated_at": datetime.now().isoformat(),
    }


def compare_candidates(
    candidates: List[Dict[str, Any]],
    criteria: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Compare multiple candidates.
    
    Args:
        candidates: List of candidate evaluation results
        criteria: Optional criteria to compare on
        
    Returns:
        Ranked list of candidates with comparison data
    """
    if criteria is None:
        criteria = ["overall_score", "interview_score", "technical_score", "cultural_fit_score"]
    
    # Add ranking for each criterion
    for criterion in criteria:
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.get(criterion, 0),
            reverse=True
        )
        for rank, candidate in enumerate(sorted_candidates, 1):
            if "rankings" not in candidate:
                candidate["rankings"] = {}
            candidate["rankings"][criterion] = rank
    
    # Calculate average ranking
    for candidate in candidates:
        rankings = candidate.get("rankings", {})
        candidate["average_rank"] = sum(rankings.values()) / len(rankings) if rankings else float('inf')
    
    # Sort by average rank
    candidates.sort(key=lambda x: x.get("average_rank", float('inf')))
    
    return candidates


def create_hiring_recommendation(
    candidate_evaluation: Dict[str, Any],
    position_requirements: Dict[str, Any],
    budget_constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create detailed hiring recommendation.
    
    Args:
        candidate_evaluation: Complete candidate evaluation
        position_requirements: Position requirements
        budget_constraints: Optional budget information
        
    Returns:
        Hiring recommendation with justification
    """
    overall_score = candidate_evaluation.get("overall_score", 0)
    recommendation = candidate_evaluation.get("recommendation", "")
    
    # Check if candidate meets minimum requirements
    meets_requirements = overall_score >= position_requirements.get("minimum_score", 70)
    
    # Check budget if provided
    within_budget = True
    salary_notes = []
    
    if budget_constraints:
        candidate_salary = candidate_evaluation.get("expected_salary", 0)
        budget_max = budget_constraints.get("max_salary", 0)
        
        if candidate_salary and budget_max:
            within_budget = candidate_salary <= budget_max
            if not within_budget:
                salary_notes.append(f"Candidate expectations (${candidate_salary:,}) exceed budget (${budget_max:,})")
    
    # Generate recommendation
    should_hire = meets_requirements and (within_budget or overall_score >= 85)
    
    justification = []
    if meets_requirements:
        justification.append(f"Candidate meets minimum requirements (score: {overall_score})")
    else:
        justification.append(f"Candidate does not meet minimum requirements (score: {overall_score})")
    
    if not within_budget and salary_notes:
        justification.extend(salary_notes)
    
    if overall_score >= 85:
        justification.append("Exceptional candidate - consider flexibility on salary")
    
    return {
        "recommend_hire": should_hire,
        "confidence": "High" if abs(overall_score - 75) > 15 else "Medium",
        "justification": justification,
        "overall_score": overall_score,
        "meets_requirements": meets_requirements,
        "within_budget": within_budget,
        "next_steps": _get_next_steps(should_hire, overall_score),
    }


def _get_next_steps(should_hire: bool, score: float) -> str:
    """Get next steps based on recommendation."""
    if should_hire:
        if score >= 85:
            return "Extend offer immediately. High priority candidate."
        else:
            return "Prepare offer letter and conduct final reference checks."
    else:
        if score >= 65:
            return "Consider for other positions or keep in talent pool."
        else:
            return "Send rejection email and close application."
