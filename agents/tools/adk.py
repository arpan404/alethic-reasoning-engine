"""
Google ADK-compliant tools for Alethic agents.

This module provides properly formatted function tools that can be directly
passed to `tools=[]` in a Google ADK Agent. The ADK automatically inspects
function signatures to generate schemas for the LLM.

Usage with ADK:
    from google.adk.agents import Agent
    from agents.tools.adk import (
        get_candidate,
        list_candidates,
        shortlist_candidate,
        ...
    )
    
    agent = Agent(
        model='gemini-2.0-flash',
        name='hiring_assistant',
        instruction='You are an AI hiring assistant...',
        tools=[
            get_candidate,
            list_candidates,
            shortlist_candidate,
            # ... add more tools
        ],
    )
"""

from typing import Optional
import logging

# Import the underlying async implementations
from agents.tools.candidates import (
    get_candidate_for_application as _get_candidate_for_application,
    list_candidates_for_job as _list_candidates_for_job,
    shortlist_candidate as _shortlist_candidate,
    reject_candidate as _reject_candidate,
    get_application_documents as _get_application_documents,
)
from agents.tools.jobs import (
    get_job as _get_job,
    list_jobs as _list_jobs,
    get_job_requirements as _get_job_requirements,
)
from agents.tools.applications import (
    get_application as _get_application,
    list_applications as _list_applications,
    move_candidate_stage as _move_candidate_stage,
)
from agents.tools.evaluations import (
    get_pre_evaluation as _get_pre_evaluation,
    get_full_evaluation as _get_full_evaluation,
    trigger_pre_evaluation as _trigger_pre_evaluation,
    trigger_full_evaluation as _trigger_full_evaluation,
    get_candidate_ranking as _get_candidate_ranking,
)
from agents.tools.interviews import (
    schedule_interview as _schedule_interview,
    get_interview_schedule as _get_interview_schedule,
)
from agents.tools.communications import (
    send_rejection_email as _send_rejection_email,
    send_interview_invitation as _send_interview_invitation,
)
from agents.tools.comparison import (
    compare_candidates_side_by_side as _compare_candidates_side_by_side,
)
from agents.tools.search import (
    search_candidates_semantic as _search_candidates_semantic,
    match_candidates_to_job as _match_candidates_to_job,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CANDIDATE TOOLS
# =============================================================================

async def get_candidate(application_id: int) -> dict:
    """
    Get detailed information about a candidate via their application.
    
    This retrieves comprehensive candidate data including contact info,
    work experience, education, skills, and AI evaluation scores.
    
    Args:
        application_id: The unique identifier of the job application.
    
    Returns:
        dict: Candidate details including name, contact, experience, 
              education, skills, and application-specific data like 
              AI scores and current stage. Returns None if not found.
    """
    return await _get_candidate_for_application(application_id)


async def list_candidates(
    job_id: int,
    stage: str = "",
    search_query: str = "",
    limit: int = 20,
) -> dict:
    """
    List candidates who have applied to a specific job.
    
    Returns a paginated list of candidates with their basic info
    and application status for the specified job.
    
    Args:
        job_id: The job ID to list candidates for.
        stage: Optional filter by application stage (e.g., 'new', 'screening', 'interview').
        search_query: Optional search term to filter by candidate name or email.
        limit: Maximum number of candidates to return (default: 20, max: 50).
    
    Returns:
        dict: Contains 'candidates' list with candidate summaries,
              'total' count, and pagination info.
    """
    return await _list_candidates_for_job(
        job_id=job_id,
        stage=stage or None,
        search_query=search_query or None,
        limit=min(limit, 50),
    )


async def shortlist_candidate(application_id: int, reason: str) -> dict:
    """
    Shortlist a candidate for further consideration.
    
    Moves the candidate to the shortlisted stage and records the reason.
    This is typically done after initial screening decides the candidate
    is a good potential fit.
    
    Args:
        application_id: The application ID to shortlist.
        reason: The reason for shortlisting (e.g., 'Strong technical skills').
    
    Returns:
        dict: Contains 'success' boolean and updated application info.
    """
    return await _shortlist_candidate(application_id=application_id, reason=reason)


async def reject_candidate(
    application_id: int,
    reason: str,
    send_email: bool = True,
) -> dict:
    """
    Reject a candidate's application.
    
    Marks the application as rejected and optionally sends a rejection
    email to the candidate. The reason is recorded for compliance.
    
    Args:
        application_id: The application ID to reject.
        reason: The reason for rejection (recorded for compliance).
        send_email: Whether to send a rejection email (default: True).
    
    Returns:
        dict: Contains 'success' boolean, rejection details, and
              'email_queued' indicating if notification was sent.
    """
    return await _reject_candidate(
        application_id=application_id,
        reason=reason,
        send_email=send_email,
    )


async def get_candidate_documents(application_id: int) -> dict:
    """
    Get all documents associated with a candidate's application.
    
    Returns the resume, cover letters, portfolio items, and other
    documents submitted with the application.
    
    Args:
        application_id: The application ID to get documents for.
    
    Returns:
        dict: Contains 'resume', 'cover_letters', 'portfolios', and
              'other_documents' lists with file information.
    """
    return await _get_application_documents(application_id)


# =============================================================================
# JOB TOOLS
# =============================================================================

async def get_job(job_id: int) -> dict:
    """
    Get detailed information about a job posting.
    
    Returns comprehensive job details including title, description,
    requirements, salary range, and application statistics.
    
    Args:
        job_id: The unique identifier of the job.
    
    Returns:
        dict: Job details including title, department, requirements,
              compensation, and current application count.
    """
    return await _get_job(job_id)


async def list_jobs(
    organization_id: int,
    status: str = "open",
    department: str = "",
    limit: int = 20,
) -> dict:
    """
    List job postings for an organization.
    
    Returns a list of jobs with optional filtering by status
    and department.
    
    Args:
        organization_id: The organization to list jobs for.
        status: Filter by job status ('open', 'closed', 'draft').
        department: Optional filter by department name.
        limit: Maximum number of jobs to return (default: 20).
    
    Returns:
        dict: Contains 'jobs' list with job summaries and 'total' count.
    """
    return await _list_jobs(
        organization_id=organization_id,
        status=status or None,
        department=department or None,
        limit=limit,
    )


async def get_job_requirements(job_id: int) -> dict:
    """
    Get detailed requirements and qualifications for a job.
    
    Returns the job's required and preferred skills, experience
    requirements, education requirements, and ideal candidate profile.
    
    Args:
        job_id: The job ID to get requirements for.
    
    Returns:
        dict: Contains 'required_skills', 'preferred_skills',
              'experience_min_years', 'education_level', and
              'ideal_candidate_description'.
    """
    return await _get_job_requirements(job_id)


# =============================================================================
# APPLICATION TOOLS
# =============================================================================

async def get_application(application_id: int) -> dict:
    """
    Get details about a specific job application.
    
    Returns application status, stage, timeline, and associated
    candidate and job information.
    
    Args:
        application_id: The unique identifier of the application.
    
    Returns:
        dict: Application details including status, stage, timestamps,
              AI scores, and candidate/job references.
    """
    return await _get_application(application_id)


async def list_applications(
    job_id: int,
    stage: str = "",
    status: str = "",
    limit: int = 20,
) -> dict:
    """
    List applications for a specific job.
    
    Returns a paginated list of applications with filtering options.
    
    Args:
        job_id: The job ID to list applications for.
        stage: Optional filter by current stage.
        status: Optional filter by status ('active', 'rejected', etc.).
        limit: Maximum number of applications to return.
    
    Returns:
        dict: Contains 'applications' list and pagination info.
    """
    return await _list_applications(
        job_id=job_id,
        stage=stage or None,
        status=status or None,
        limit=limit,
    )


async def move_candidate_stage(
    application_id: int,
    new_stage: str,
    reason: str = "",
) -> dict:
    """
    Move a candidate to a different stage in the hiring pipeline.
    
    Updates the application's current stage (e.g., from 'screening'
    to 'interview'). Records the transition for audit purposes.
    
    Args:
        application_id: The application to move.
        new_stage: The target stage (e.g., 'interview', 'offer', 'hired').
        reason: Optional reason for the stage change.
    
    Returns:
        dict: Contains 'success' boolean and stage transition details.
    """
    return await _move_candidate_stage(
        application_id=application_id,
        new_stage=new_stage,
        reason=reason or None,
    )


# =============================================================================
# EVALUATION TOOLS
# =============================================================================

async def get_pre_evaluation(application_id: int) -> dict:
    """
    Get the AI pre-evaluation results for an application.
    
    Returns the quick initial screening scores that assess
    basic qualification match before full evaluation.
    
    Args:
        application_id: The application to get pre-evaluation for.
    
    Returns:
        dict: Contains screening scores, match assessment, and
              initial recommendation.
    """
    return await _get_pre_evaluation(application_id)


async def get_full_evaluation(application_id: int) -> dict:
    """
    Get the comprehensive AI evaluation for an application.
    
    Returns detailed analysis including skills assessment, experience
    evaluation, role fit scores, and hiring recommendation.
    
    Args:
        application_id: The application to get full evaluation for.
    
    Returns:
        dict: Contains detailed scores for skills, experience, culture
              fit, growth potential, and overall recommendation.
    """
    return await _get_full_evaluation(application_id)


async def trigger_evaluation(
    application_id: int,
    evaluation_type: str = "full",
) -> dict:
    """
    Trigger an AI evaluation for an application.
    
    Queues an evaluation job to analyze the candidate's profile
    against the job requirements.
    
    Args:
        application_id: The application to evaluate.
        evaluation_type: Type of evaluation - 'pre' for quick screening
                        or 'full' for comprehensive analysis.
    
    Returns:
        dict: Contains 'success' boolean and 'task_id' for tracking.
    """
    if evaluation_type == "pre":
        return await _trigger_pre_evaluation(application_id)
    return await _trigger_full_evaluation(application_id)


async def get_candidate_ranking(job_id: int, limit: int = 10) -> dict:
    """
    Get AI-ranked candidates for a job.
    
    Returns candidates sorted by their AI evaluation scores,
    showing the best-matched candidates first.
    
    Args:
        job_id: The job to get rankings for.
        limit: Maximum number of candidates to return (default: 10).
    
    Returns:
        dict: Contains 'rankings' list ordered by AI score, with
              candidate info and score breakdowns.
    """
    return await _get_candidate_ranking(job_id=job_id, limit=limit)


# =============================================================================
# INTERVIEW TOOLS
# =============================================================================

async def schedule_interview(
    application_id: int,
    interview_type: str,
    interviewer_ids: list,
    duration_minutes: int = 60,
) -> dict:
    """
    Schedule an interview for a candidate.
    
    Creates an interview and optionally sends calendar invites
    to interviewers and the candidate.
    
    Args:
        application_id: The application to schedule interview for.
        interview_type: Type of interview ('phone', 'technical', 'onsite').
        interviewer_ids: List of user IDs for interviewers.
        duration_minutes: Interview duration in minutes (default: 60).
    
    Returns:
        dict: Contains 'success' boolean and interview details
              including scheduled time slots.
    """
    return await _schedule_interview(
        application_id=application_id,
        interview_type=interview_type,
        interviewer_ids=interviewer_ids,
        duration_minutes=duration_minutes,
    )


async def get_interview_schedule(application_id: int) -> dict:
    """
    Get scheduled interviews for an application.
    
    Returns all past and upcoming interviews with their status,
    timing, and interviewer information.
    
    Args:
        application_id: The application to get interviews for.
    
    Returns:
        dict: Contains 'interviews' list with schedule details,
              status, and interviewer info.
    """
    return await _get_interview_schedule(application_id)


# =============================================================================
# COMMUNICATION TOOLS
# =============================================================================

async def send_rejection_email(
    application_id: int,
    template_id: int = 0,
) -> dict:
    """
    Send a rejection email to a candidate.
    
    Queues a rejection email using the specified template.
    If no template is specified, uses the default template.
    
    Args:
        application_id: The application to send rejection for.
        template_id: Optional email template ID (0 for default).
    
    Returns:
        dict: Contains 'success' boolean and 'task_id' for tracking.
    """
    return await _send_rejection_email(
        application_id=application_id,
        template_id=template_id or None,
    )


async def send_interview_invitation(
    application_id: int,
    interview_id: int,
) -> dict:
    """
    Send an interview invitation email to a candidate.
    
    Sends an email with interview details including date, time,
    location/link, and any preparation instructions.
    
    Args:
        application_id: The application to send invitation for.
        interview_id: The interview to send invitation for.
    
    Returns:
        dict: Contains 'success' boolean and 'task_id' for tracking.
    """
    return await _send_interview_invitation(
        application_id=application_id,
        interview_id=interview_id,
    )


# =============================================================================
# COMPARISON TOOLS
# =============================================================================

async def compare_candidates(application_ids: list) -> dict:
    """
    Compare multiple candidates side-by-side.
    
    Returns detailed comparison data for 2-5 candidates including
    their qualifications, scores, and how they match the job.
    
    Args:
        application_ids: List of 2-5 application IDs to compare.
    
    Returns:
        dict: Contains comparison data for each candidate, common
              skills, unique strengths, and ranking dimensions.
    """
    return await _compare_candidates_side_by_side(application_ids)


# =============================================================================
# SEARCH TOOLS
# =============================================================================

async def search_candidates(
    query: str,
    job_id: int = 0,
    limit: int = 10,
) -> dict:
    """
    Semantically search for candidates matching a natural language query.
    
    Uses AI embeddings to find candidates whose profiles best match
    the search query. Good for queries like "React developers with
    5+ years experience" or "ML engineers from FAANG companies".
    
    Args:
        query: Natural language search query describing ideal candidates.
        job_id: Optional job ID to filter to that job's applicants only.
        limit: Maximum number of results (default: 10).
    
    Returns:
        dict: Contains 'matches' list with ranked candidates and
              similarity scores.
    """
    return await _search_candidates_semantic(
        query=query,
        job_id=job_id or None,
        limit=limit,
    )


async def find_best_matches(job_id: int, limit: int = 20) -> dict:
    """
    Find candidates that best match a job semantically.
    
    Uses AI to analyze job requirements and find candidates
    whose profiles best match, combining semantic similarity
    with AI evaluation scores.
    
    Args:
        job_id: The job to find matching candidates for.
        limit: Maximum number of matches to return (default: 20).
    
    Returns:
        dict: Contains 'matches' list with ranked candidates,
              semantic similarity, and combined scores.
    """
    return await _match_candidates_to_job(job_id=job_id, limit=limit)


# =============================================================================
# EXPORT - All ADK-compliant tools
# =============================================================================

__all__ = [
    # Candidate tools
    "get_candidate",
    "list_candidates",
    "shortlist_candidate",
    "reject_candidate",
    "get_candidate_documents",
    # Job tools
    "get_job",
    "list_jobs",
    "get_job_requirements",
    # Application tools
    "get_application",
    "list_applications",
    "move_candidate_stage",
    # Evaluation tools
    "get_pre_evaluation",
    "get_full_evaluation",
    "trigger_evaluation",
    "get_candidate_ranking",
    # Interview tools
    "schedule_interview",
    "get_interview_schedule",
    # Communication tools
    "send_rejection_email",
    "send_interview_invitation",
    # Comparison tools
    "compare_candidates",
    # Search tools
    "search_candidates",
    "find_best_matches",
]
