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

from typing import Optional, List
from datetime import datetime
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
    get_interview_analysis as _get_interview_analysis,
    generate_interview_questions as _generate_interview_questions,
)
from agents.tools.communications import (
    send_rejection_email as _send_rejection_email,
    send_interview_invitation as _send_interview_invitation,
    get_email_templates as _get_email_templates,
    get_communication_history as _get_communication_history,
)
from agents.tools.documents import (
    read_resume as _read_resume,
    read_cover_letter as _read_cover_letter,
    read_linkedin_profile as _read_linkedin_profile,
    read_portfolio as _read_portfolio,
)
from agents.tools.bulk import (
    upload_resumes_bulk as _upload_resumes_bulk,
    get_bulk_upload_status as _get_bulk_upload_status,
    bulk_reject_candidates as _bulk_reject_candidates,
    bulk_move_stage as _bulk_move_stage,
)
from agents.tools.comparison import (
    compare_candidates_side_by_side as _compare_candidates_side_by_side,
)
from agents.tools.background_checks import (
    initiate_background_check as _initiate_background_check,
    track_background_check_status as _track_background_check_status,
    get_background_check_results as _get_background_check_results,
)
from agents.tools.compliance import (
    generate_adverse_action_notice as _generate_adverse_action_notice,
    verify_work_authorization as _verify_work_authorization,
    generate_eeo_report as _generate_eeo_report,
)
from agents.tools.calendar import (
    find_available_time_slots as _find_available_time_slots,
    create_calendar_event as _create_calendar_event,
    get_calendar_availability as _get_calendar_availability,
)
from agents.tools.search import (
    search_candidates_semantic as _search_candidates_semantic,
    find_similar_candidates as _find_similar_candidates,
    match_candidates_to_job as _match_candidates_to_job,
    vectorize_application as _vectorize_application,
)
from agents.tools.queue import (
    get_task_status as _get_task_status,
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
    scheduled_at: str,
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
        scheduled_at: Interview time in ISO format (YYYY-MM-DDTHH:MM:SS).
        duration_minutes: Interview duration in minutes (default: 60).
    
    Returns:
        dict: Contains 'success' boolean and interview details
              including scheduled time slots.
    """
    try:
        dt = datetime.fromisoformat(scheduled_at)
    except ValueError:
        return {"success": False, "error": "Invalid date format. Use ISO format."}

    return await _schedule_interview(
        application_id=application_id,
        interview_type=interview_type,
        interviewer_ids=interviewer_ids,
        scheduled_at=dt,
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
# DOCUMENT TOOLS
# =============================================================================

async def read_resume(application_id: int) -> dict:
    """
    Read the parsed resume content for an application.
    
    Returns structured resume data including contact info, work history,
    education, skills, and the raw text content.
    
    Args:
        application_id: The application to read resume for.
    
    Returns:
        dict: Parsed resume data with contact info, experience,
              education, skills, and raw text content.
    """
    result = await _read_resume(application_id)
    return result or {"success": False, "error": "Resume not found"}


async def read_cover_letter(application_id: int) -> dict:
    """
    Read the cover letter content for an application.
    
    Returns the full text of the candidate's cover letter if one
    was submitted with the application.
    
    Args:
        application_id: The application to read cover letter for.
    
    Returns:
        dict: Contains 'has_cover_letter' boolean and 'content' text.
    """
    result = await _read_cover_letter(application_id)
    return result or {"success": False, "error": "Cover letter not found"}


async def read_linkedin_profile(application_id: int) -> dict:
    """
    Read LinkedIn profile data for a candidate.
    
    Returns imported LinkedIn data if the candidate connected their
    profile, including connections, endorsements, and recommendations.
    
    Args:
        application_id: The application to read LinkedIn data for.
    
    Returns:
        dict: LinkedIn profile data including headline, experience,
              skills, endorsements, and connection count.
    """
    result = await _read_linkedin_profile(application_id)
    return result or {"success": False, "error": "LinkedIn data not available"}


async def read_portfolio(application_id: int) -> dict:
    """
    Read portfolio items for an application.
    
    Returns portfolio files, links, and GitHub/website URLs
    associated with the candidate.
    
    Args:
        application_id: The application to read portfolio for.
    
    Returns:
        dict: Contains 'items' list with portfolio files and links.
    """
    return await _read_portfolio(application_id)


# =============================================================================
# BULK OPERATION TOOLS
# =============================================================================

async def upload_resumes_bulk(
    job_id: int,
    file_urls: list,
    source: str = "bulk_upload",
) -> dict:
    """
    Upload multiple resumes in bulk for a job.
    
    Queues processing of multiple resume files. Each resume will
    be parsed and a new application will be created.
    
    Args:
        job_id: The job to create applications for.
        file_urls: List of URLs to resume files.
        source: Source label for the uploads (default: 'bulk_upload').
    
    Returns:
        dict: Contains 'task_id' to track bulk processing status.
    """
    return await _upload_resumes_bulk(
        job_id=job_id,
        file_urls=file_urls,
        source=source,
    )


async def get_bulk_upload_status(task_id: str) -> dict:
    """
    Get the status of a bulk upload operation.
    
    Returns progress information for an ongoing bulk upload,
    including how many resumes have been processed.
    
    Args:
        task_id: The task ID from upload_resumes_bulk.
    
    Returns:
        dict: Contains 'status', 'progress', 'completed', 'failed' counts.
    """
    return await _get_bulk_upload_status(task_id)


async def bulk_reject_candidates(
    application_ids: list,
    reason: str,
    send_emails: bool = True,
) -> dict:
    """
    Reject multiple candidates at once.
    
    Efficiently rejects a batch of applications with the same reason.
    Optionally sends rejection emails to all candidates.
    
    Args:
        application_ids: List of application IDs to reject.
        reason: The rejection reason (applies to all).
        send_emails: Whether to send rejection emails (default: True).
    
    Returns:
        dict: Contains 'task_id' to track bulk rejection status.
    """
    return await _bulk_reject_candidates(
        application_ids=application_ids,
        reason=reason,
        send_emails=send_emails,
    )


async def bulk_move_stage(
    application_ids: list,
    new_stage: str,
    reason: str = "",
) -> dict:
    """
    Move multiple candidates to a new stage at once.
    
    Efficiently updates the stage for multiple applications.
    Useful for batch advancing candidates after group decisions.
    
    Args:
        application_ids: List of application IDs to move.
        new_stage: The target stage for all applications.
        reason: Optional reason for the stage change.
    
    Returns:
        dict: Contains 'task_id' to track bulk operation status.
    """
    return await _bulk_move_stage(
        application_ids=application_ids,
        new_stage=new_stage,
        reason=reason or None,
    )


# =============================================================================
# BACKGROUND CHECK TOOLS
# =============================================================================

async def start_background_check(
    application_id: int,
    check_types: list,
    provider: str = "default",
) -> dict:
    """
    Initiate a background check for a candidate.
    
    Starts a background verification process with an external provider.
    Check types can include criminal, employment, education, etc.
    
    Args:
        application_id: The application to run background check on.
        check_types: Types of checks to run ('criminal', 'employment', 'education', 'credit').
        provider: Background check provider ('default', 'checkr', 'sterling').
    
    Returns:
        dict: Contains 'request_id' to track the background check.
    """
    return await _initiate_background_check(
        application_id=application_id,
        check_types=check_types,
        provider=provider,
    )


async def get_background_check_status(request_id: str) -> dict:
    """
    Check the status of an ongoing background check.
    
    Returns the current status and any available interim results
    for a background check request.
    
    Args:
        request_id: The background check request ID.
    
    Returns:
        dict: Contains 'status', 'checks_completed', 'checks_pending'.
    """
    return await _track_background_check_status(request_id)


async def get_background_check_results(request_id: str) -> dict:
    """
    Get the full results of a completed background check.
    
    Returns detailed results for each check type including
    any flags, concerns, or verification failures.
    
    Args:
        request_id: The background check request ID.
    
    Returns:
        dict: Contains detailed results for each check type,
              flags, and overall assessment.
    """
    return await _get_background_check_results(request_id)


# =============================================================================
# COMPLIANCE TOOLS
# =============================================================================

async def generate_adverse_action_notice(
    application_id: int,
    notice_type: str,
    reasons: list,
) -> dict:
    """
    Generate an FCRA-compliant adverse action notice.
    
    Creates the legally required notice when rejecting a candidate
    based on background check results. Required for FCRA compliance.
    
    Args:
        application_id: The application this notice is for.
        notice_type: Type of notice ('pre_adverse', 'adverse').
        reasons: List of reasons for the adverse action.
    
    Returns:
        dict: Contains generated notice and required next steps.
    """
    return await _generate_adverse_action_notice(
        application_id=application_id,
        notice_type=notice_type,
        reasons=reasons,
    )


async def verify_work_authorization(
    application_id: int,
    document_type: str,
    document_number: str,
    expiration_date: str = "",
) -> dict:
    """
    Verify I-9 work authorization for a candidate.
    
    Initiates E-Verify or similar work authorization verification.
    Required for employment eligibility verification.
    
    Args:
        application_id: The application to verify.
        document_type: Type of document ('us_passport', 'permanent_resident_card', etc.).
        document_number: The document identification number.
        expiration_date: Document expiration date in YYYY-MM-DD format.
    
    Returns:
        dict: Contains verification 'task_id' and 'status'.
    """
    exp_date = None
    if expiration_date:
        try:
            exp_date = datetime.strptime(expiration_date, "%Y-%m-%d")
        except ValueError:
            pass
    
    return await _verify_work_authorization(
        application_id=application_id,
        document_type=document_type,
        document_number=document_number,
        expiration_date=exp_date,
    )


async def generate_eeo_report(
    organization_id: int,
    report_period: str,
) -> dict:
    """
    Generate an EEO-1 compliance report.
    
    Creates the Equal Employment Opportunity report for the
    specified time period. Required for federal compliance.
    
    Args:
        organization_id: The organization to generate report for.
        report_period: Report period in 'YYYY' or 'YYYY-Q1' format.
    
    Returns:
        dict: Contains 'task_id' for report generation tracking.
    """
    return await _generate_eeo_report(
        organization_id=organization_id,
        report_period=report_period,
    )


# =============================================================================
# CALENDAR TOOLS
# =============================================================================

async def find_available_slots(
    user_ids: list,
    duration_minutes: int = 60,
    date_range_days: int = 7,
) -> dict:
    """
    Find available time slots for a meeting.
    
    Checks calendars of specified users and finds overlapping
    availability for scheduling interviews or meetings.
    
    Args:
        user_ids: List of user IDs whose calendars to check.
        duration_minutes: Required meeting duration (default: 60).
        date_range_days: How many days ahead to search (default: 7).
    
    Returns:
        dict: Contains 'available_slots' list with date/time options.
    """
    return await _find_available_time_slots(
        user_ids=user_ids,
        duration_minutes=duration_minutes,
        date_range_days=date_range_days,
    )


async def create_calendar_event(
    title: str,
    start_time: str,
    duration_minutes: int,
    attendee_ids: list,
    description: str = "",
    location: str = "",
) -> dict:
    """
    Create a calendar event for an interview or meeting.
    
    Creates the event and sends invitations to all attendees.
    Supports virtual meeting links if location is a URL.
    
    Args:
        title: Event title (e.g., 'Interview - John Smith').
        start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
        duration_minutes: Event duration in minutes.
        attendee_ids: List of user IDs to invite.
        description: Optional event description.
        location: Physical location or video call URL.
    
    Returns:
        dict: Contains 'event_id' and 'calendar_links' for attendees.
    """
    return await _create_calendar_event(
        title=title,
        start_time=start_time,
        duration_minutes=duration_minutes,
        attendee_ids=attendee_ids,
        description=description or None,
        location=location or None,
    )


async def get_user_availability(user_id: int, date: str = "") -> dict:
    """
    Get calendar availability for a user.
    
    Returns free/busy status for the specified date,
    showing available time blocks.
    
    Args:
        user_id: The user to check availability for.
        date: Date to check in YYYY-MM-DD format (default: today).
    
    Returns:
        dict: Contains 'available_slots' and 'busy_slots' for the day.
    """
    return await _get_calendar_availability(
        user_id=user_id,
        date=date or None,
    )


# =============================================================================
# ADDITIONAL INTERVIEW TOOLS
# =============================================================================

async def get_interview_analysis(interview_id: int) -> dict:
    """
    Get AI analysis of a completed interview.
    
    Returns the AI's assessment of the interview including
    performance scores, key observations, and recommendations.
    
    Args:
        interview_id: The interview to get analysis for.
    
    Returns:
        dict: Contains scores, observations, and hiring recommendation.
    """
    return await _get_interview_analysis(interview_id)


async def generate_interview_questions(
    application_id: int,
    interview_type: str = "general",
    focus_areas: list = None,
) -> dict:
    """
    Generate tailored interview questions for a candidate.
    
    Creates questions based on the candidate's background
    and the job requirements. Can focus on specific areas.
    
    Args:
        application_id: The application to generate questions for.
        interview_type: Type of interview ('general', 'technical', 'behavioral').
        focus_areas: Optional list of areas to focus questions on.
    
    Returns:
        dict: Contains 'questions' list with suggested interview questions.
    """
    return await _generate_interview_questions(
        application_id=application_id,
        interview_type=interview_type,
        focus_areas=focus_areas or [],
    )


# =============================================================================
# ADDITIONAL COMMUNICATION TOOLS
# =============================================================================

async def get_email_templates(organization_id: int, template_type: str = "") -> dict:
    """
    Get available email templates for an organization.
    
    Returns templates that can be used for candidate communications
    like rejections, interview invites, and offers.
    
    Args:
        organization_id: The organization to get templates for.
        template_type: Optional filter by type ('rejection', 'interview', 'offer').
    
    Returns:
        dict: Contains 'templates' list with template details.
    """
    return await _get_email_templates(
        organization_id=organization_id,
        template_type=template_type or None,
    )


async def get_communication_history(application_id: int) -> dict:
    """
    Get all communications sent to a candidate.
    
    Returns the history of emails and messages sent to the
    candidate for this application.
    
    Args:
        application_id: The application to get history for.
    
    Returns:
        dict: Contains 'communications' list with sent messages.
    """
    return await _get_communication_history(application_id)


# =============================================================================
# ADDITIONAL SEARCH TOOLS
# =============================================================================

async def find_similar_candidates(
    reference_application_id: int,
    job_id: int,
    limit: int = 10,
) -> dict:
    """
    Find candidates similar to a reference candidate.
    
    Uses AI to find candidates with similar profiles to a candidate
    you already like. Useful for "find more like this" searches.
    
    Args:
        reference_application_id: The application of the candidate to match.
        job_id: The job to search within.
        limit: Maximum number of similar candidates to return.
    
    Returns:
        dict: Contains 'similar_candidates' list with similarity scores.
    """
    return await _find_similar_candidates(
        reference_application_id=reference_application_id,
        job_id=job_id,
        limit=limit,
    )


async def vectorize_candidate(application_id: int) -> dict:
    """
    Generate/update AI embeddings for a candidate.
    
    Triggers vectorization of the candidate's profile and documents
    to enable semantic search and matching.
    
    Args:
        application_id: The application to vectorize.
    
    Returns:
        dict: Contains 'task_id' for tracking vectorization.
    """
    return await _vectorize_application(application_id=application_id)


# =============================================================================
# TASK TRACKING TOOLS
# =============================================================================

async def get_task_status(task_id: str) -> dict:
    """
    Get the status of a queued task.
    
    Checks the status of background jobs like bulk operations,
    email sending, or AI evaluations.
    
    Args:
        task_id: The task ID to check status for.
    
    Returns:
        dict: Contains 'status', 'progress', and 'result' if completed.
    """
    return await _get_task_status(task_id)


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
    "get_interview_analysis",
    "generate_interview_questions",
    # Communication tools
    "send_rejection_email",
    "send_interview_invitation",
    "get_email_templates",
    "get_communication_history",
    # Document tools
    "read_resume",
    "read_cover_letter",
    "read_linkedin_profile",
    "read_portfolio",
    # Bulk operation tools
    "upload_resumes_bulk",
    "get_bulk_upload_status",
    "bulk_reject_candidates",
    "bulk_move_stage",
    # Comparison tools
    "compare_candidates",
    # Background check tools
    "start_background_check",
    "get_background_check_status",
    "get_background_check_results",
    # Compliance tools
    "generate_adverse_action_notice",
    "verify_work_authorization",
    "generate_eeo_report",
    # Calendar tools
    "find_available_slots",
    "create_calendar_event",
    "get_user_availability",
    # Search tools
    "search_candidates",
    "find_best_matches",
    "find_similar_candidates",
    "vectorize_candidate",
    # Task tracking
    "get_task_status",
]
