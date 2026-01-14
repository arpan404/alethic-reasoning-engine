"""
Action-oriented tools for Alethic LLM agents.

These tools provide database operations and external system interactions
that LLMs cannot perform natively. They are designed to be used by the
chat-first AI hiring copilot to perform actions on behalf of users.
"""

from agents.tools.candidates import (
    get_candidate,
    list_candidates,
    update_candidate_status,
    shortlist_candidate,
    reject_candidate,
    get_candidate_documents,
)
from agents.tools.jobs import (
    get_job,
    list_jobs,
    get_job_requirements,
)
from agents.tools.applications import (
    get_application,
    list_applications,
    move_candidate_stage,
    get_application_history,
)
from agents.tools.evaluations import (
    get_pre_evaluation,
    get_full_evaluation,
    get_prescreening_results,
    trigger_pre_evaluation,
    trigger_full_evaluation,
    get_candidate_ranking,
)
from agents.tools.interviews import (
    schedule_interview,
    get_interview_schedule,
    get_interview_analysis,
    generate_interview_questions,
)
from agents.tools.communications import (
    send_rejection_email,
    send_interview_invitation,
    get_email_templates,
    get_communication_history,
)
from agents.tools.documents import (
    read_resume,
    read_cover_letter,
    read_linkedin_profile,
    read_portfolio,
)
from agents.tools.bulk import (
    upload_resumes_bulk,
    get_bulk_upload_status,
    bulk_reject_candidates,
    bulk_move_stage,
)
from agents.tools.comparison import (
    compare_candidates_side_by_side,
)
from agents.tools.queue import (
    enqueue_task,
    get_task_status,
    cancel_task,
)
from agents.tools.background_checks import (
    initiate_background_check,
    track_background_check_status,
    get_background_check_results,
)
from agents.tools.compliance import (
    generate_adverse_action_notice,
    verify_work_authorization,
    generate_eeo_report,
)
from agents.tools.calendar import (
    find_available_time_slots,
    create_calendar_event,
    get_calendar_availability,
)
from agents.tools.search import (
    search_candidates_semantic,
    find_similar_candidates,
    match_candidates_to_job,
    vectorize_candidate,
)

__all__ = [
    # Candidates
    "get_candidate",
    "list_candidates",
    "update_candidate_status",
    "shortlist_candidate",
    "reject_candidate",
    "get_candidate_documents",
    # Jobs
    "get_job",
    "list_jobs",
    "get_job_requirements",
    # Applications
    "get_application",
    "list_applications",
    "move_candidate_stage",
    "get_application_history",
    # Evaluations
    "get_pre_evaluation",
    "get_full_evaluation",
    "get_prescreening_results",
    "trigger_pre_evaluation",
    "trigger_full_evaluation",
    "get_candidate_ranking",
    # Interviews
    "schedule_interview",
    "get_interview_schedule",
    "get_interview_analysis",
    "generate_interview_questions",
    # Communications
    "send_rejection_email",
    "send_interview_invitation",
    "get_email_templates",
    "get_communication_history",
    # Documents
    "read_resume",
    "read_cover_letter",
    "read_linkedin_profile",
    "read_portfolio",
    # Bulk
    "upload_resumes_bulk",
    "get_bulk_upload_status",
    "bulk_reject_candidates",
    "bulk_move_stage",
    # Comparison
    "compare_candidates_side_by_side",
    # Queue
    "enqueue_task",
    "get_task_status",
    "cancel_task",
    # Background Checks
    "initiate_background_check",
    "track_background_check_status",
    "get_background_check_results",
    # Compliance
    "generate_adverse_action_notice",
    "verify_work_authorization",
    "generate_eeo_report",
    # Calendar
    "find_available_time_slots",
    "create_calendar_event",
    "get_calendar_availability",
    # Vector Search
    "search_candidates_semantic",
    "find_similar_candidates",
    "match_candidates_to_job",
    "vectorize_candidate",
]
