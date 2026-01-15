"""
API Services Layer.

Direct database operations for API endpoints,
separate from AI agent tools.
"""

from api.services.candidates import (
    get_candidate,
    list_candidates,
    shortlist_candidate,
    reject_candidate,
    get_candidate_documents,
)

from api.services.applications import (
    get_application,
    list_applications,
    move_application_stage,
    get_application_history,
)

from api.services.jobs import (
    get_job,
    list_jobs,
    get_job_requirements,
)

from api.services.interviews import (
    schedule_interview,
    list_interviews,
    get_interview,
    cancel_interview,
    reschedule_interview,
)

from api.services.evaluations import (
    get_pre_evaluation,
    get_full_evaluation,
    get_prescreening,
    trigger_evaluation,
    get_candidate_rankings,
)

from api.services.documents import (
    get_resume,
    get_cover_letter,
    get_linkedin_profile,
    get_portfolio,
    get_all_documents,
)

from api.services.search import (
    semantic_search,
    find_similar_candidates,
    match_candidates_to_job,
)

from api.services.comparison import (
    compare_candidates,
)

from api.services.calendar import (
    get_user_availability,
    find_available_slots,
    create_calendar_event,
)

from api.services.bulk import (
    upload_resumes_bulk,
    get_bulk_upload_status,
    bulk_reject_candidates,
    bulk_move_stage,
)

from api.services.background_checks import (
    initiate_background_check,
    get_background_check_status,
    get_background_check_results,
)

from api.services.compliance import (
    generate_adverse_action_notice,
    verify_work_authorization,
    export_user_data,
    erase_user_data,
    generate_eeo_report,
)

from api.services.offers import (
    create_offer,
    get_offer,
    list_offers,
    update_offer,
    send_offer,
    withdraw_offer,
    record_offer_response,
)

from api.services.users import (
    get_user,
    list_users,
    update_user,
    deactivate_user,
    get_user_permissions,
)

from api.services.webhooks import (
    register_webhook,
    list_webhooks,
    get_webhook,
    update_webhook,
    delete_webhook,
    test_webhook,
    get_webhook_deliveries,
)

from api.services.communications import (
    send_email,
    get_email_templates,
    get_communication_history,
)

__all__ = [
    # Candidates
    "get_candidate",
    "list_candidates",
    "shortlist_candidate",
    "reject_candidate",
    "get_candidate_documents",
    # Applications
    "get_application",
    "list_applications",
    "move_application_stage",
    "get_application_history",
    # Jobs
    "get_job",
    "list_jobs",
    "get_job_requirements",
    # Interviews
    "schedule_interview",
    "list_interviews",
    "get_interview",
    "cancel_interview",
    "reschedule_interview",
    # Evaluations
    "get_pre_evaluation",
    "get_full_evaluation",
    "get_prescreening",
    "trigger_evaluation",
    "get_candidate_rankings",
    # Documents
    "get_resume",
    "get_cover_letter",
    "get_linkedin_profile",
    "get_portfolio",
    "get_all_documents",
    # Search
    "semantic_search",
    "find_similar_candidates",
    "match_candidates_to_job",
    # Comparison
    "compare_candidates",
    # Calendar
    "get_user_availability",
    "find_available_slots",
    "create_calendar_event",
    # Bulk
    "upload_resumes_bulk",
    "get_bulk_upload_status",
    "bulk_reject_candidates",
    "bulk_move_stage",
    # Background Checks
    "initiate_background_check",
    "get_background_check_status",
    "get_background_check_results",
    # Compliance
    "generate_adverse_action_notice",
    "verify_work_authorization",
    "export_user_data",
    "erase_user_data",
    "generate_eeo_report",
    # Offers
    "create_offer",
    "get_offer",
    "list_offers",
    "update_offer",
    "send_offer",
    "withdraw_offer",
    "record_offer_response",
    # Users
    "get_user",
    "list_users",
    "update_user",
    "deactivate_user",
    "get_user_permissions",
    # Webhooks
    "register_webhook",
    "list_webhooks",
    "get_webhook",
    "update_webhook",
    "delete_webhook",
    "test_webhook",
    "get_webhook_deliveries",
    # Communications
    "send_email",
    "get_email_templates",
    "get_communication_history",
]
