"""Email composition and sending tools for agents."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def compose_interview_invitation(
    candidate_name: str,
    job_title: str,
    company_name: str,
    interview_date: datetime,
    interview_duration: int,
    interview_type: str,
    interviewer_name: str,
    additional_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Compose interview invitation email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        interview_date: Date and time of interview
        interview_duration: Duration in minutes
        interview_type: Type (phone, video, in-person)
        interviewer_name: Name of interviewer
        additional_details: Optional additional details
        
    Returns:
        Dictionary with subject and body
    """
    subject = f"Interview Invitation - {job_title} at {company_name}"
    
    meeting_link = additional_details.get("meeting_link", "") if additional_details else ""
    location = additional_details.get("location", "") if additional_details else ""
    
    body = f"""Dear {candidate_name},

We are pleased to invite you to interview for the {job_title} position at {company_name}.

Interview Details:
- Date: {interview_date.strftime('%A, %B %d, %Y')}
- Time: {interview_date.strftime('%I:%M %p %Z')}
- Duration: {interview_duration} minutes
- Type: {interview_type}
- Interviewer: {interviewer_name}
"""
    
    if meeting_link:
        body += f"\nMeeting Link: {meeting_link}\n"
    
    if location:
        body += f"\nLocation: {location}\n"
    
    body += """
Please confirm your availability by replying to this email.

If you need to reschedule, please let us know as soon as possible.

We look forward to speaking with you!

Best regards,
{company_name} Recruiting Team
"""
    
    return {
        "subject": subject,
        "body": body.format(company_name=company_name),
    }


def compose_rejection_email(
    candidate_name: str,
    job_title: str,
    company_name: str,
    personalized_feedback: Optional[str] = None,
    keep_in_pool: bool = False,
) -> Dict[str, str]:
    """Compose rejection email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        personalized_feedback: Optional personalized feedback
        keep_in_pool: Whether to keep in talent pool
        
    Returns:
        Dictionary with subject and body
    """
    subject = f"Update on your application - {job_title} at {company_name}"
    
    body = f"""Dear {candidate_name},

Thank you for taking the time to apply for the {job_title} position at {company_name} and for your interest in our company.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match our current needs.
"""
    
    if personalized_feedback:
        body += f"\n{personalized_feedback}\n"
    
    if keep_in_pool:
        body += """
However, we were impressed by your background and would like to keep your information on file for future opportunities that may be a better fit.
"""
    
    body += f"""
We encourage you to apply for other positions at {company_name} that match your skills and experience.

Thank you again for your interest in {company_name}.

Best regards,
{company_name} Recruiting Team
"""
    
    return {
        "subject": subject,
        "body": body,
    }


def compose_offer_letter(
    candidate_name: str,
    job_title: str,
    company_name: str,
    salary: float,
    start_date: datetime,
    benefits: List[str],
    additional_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Compose job offer letter email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        salary: Annual salary
        start_date: Proposed start date
        benefits: List of benefits
        additional_details: Optional additional details
        
    Returns:
        Dictionary with subject and body
    """
    subject = f"Job Offer - {job_title} at {company_name}"
    
    bonus = additional_details.get("bonus", "") if additional_details else ""
    equity = additional_details.get("equity", "") if additional_details else ""
    
    body = f"""Dear {candidate_name},

We are delighted to extend an offer for the position of {job_title} at {company_name}.

Offer Details:
- Position: {job_title}
- Annual Salary: ${salary:,.2f}
"""
    
    if bonus:
        body += f"- Annual Bonus: {bonus}\n"
    
    if equity:
        body += f"- Equity: {equity}\n"
    
    body += f"- Start Date: {start_date.strftime('%B %d, %Y')}\n\n"
    
    body += "Benefits:\n"
    for benefit in benefits:
        body += f"- {benefit}\n"
    
    body += f"""
Please review the attached formal offer letter and sign it by {(datetime.now() + timedelta(days=7)).strftime('%B %d, %Y')}.

If you have any questions, please don't hesitate to reach out.

We are excited about the possibility of you joining our team!

Best regards,
{company_name} Recruiting Team
"""
    
    return {
        "subject": subject,
        "body": body,
    }


def compose_application_confirmation(
    candidate_name: str,
    job_title: str,
    company_name: str,
    next_steps: Optional[str] = None,
) -> Dict[str, str]:
    """Compose application confirmation email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        next_steps: Optional next steps information
        
    Returns:
        Dictionary with subject and body
    """
    subject = f"Application Received - {job_title} at {company_name}"
    
    body = f"""Dear {candidate_name},

Thank you for applying to the {job_title} position at {company_name}!

We have received your application and our team is currently reviewing it.
"""
    
    if next_steps:
        body += f"\n{next_steps}\n"
    else:
        body += """
If your qualifications match our needs, we will contact you within 1-2 weeks to schedule an interview.
"""
    
    body += f"""
In the meantime, feel free to explore more about {company_name} on our website.

Thank you for your interest in joining our team!

Best regards,
{company_name} Recruiting Team
"""
    
    return {
        "subject": subject,
        "body": body,
    }


def compose_status_update(
    candidate_name: str,
    job_title: str,
    company_name: str,
    current_stage: str,
    expected_timeline: Optional[str] = None,
) -> Dict[str, str]:
    """Compose application status update email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        current_stage: Current stage in process
        expected_timeline: Optional expected timeline
        
    Returns:
        Dictionary with subject and body
    """
    subject = f"Application Status Update - {job_title} at {company_name}"
    
    body = f"""Dear {candidate_name},

We wanted to provide you with an update on your application for the {job_title} position at {company_name}.

Your application is currently in the {current_stage} stage of our hiring process.
"""
    
    if expected_timeline:
        body += f"\n{expected_timeline}\n"
    
    body += """
We appreciate your patience and continued interest in this opportunity.

If you have any questions, please don't hesitate to reach out.

Best regards,
{company_name} Recruiting Team
"""
    
    return {
        "subject": subject,
        "body": body,
    }


def personalize_email_template(
    template: str,
    placeholders: Dict[str, str],
) -> str:
    """Personalize email template with candidate-specific information.
    
    Args:
        template: Email template with {placeholders}
        placeholders: Dictionary of placeholder values
        
    Returns:
        Personalized email
    """
    try:
        return template.format(**placeholders)
    except KeyError as e:
        logger.error(f"Missing placeholder in template: {e}")
        return template


def validate_email_content(
    subject: str,
    body: str,
    required_elements: Optional[List[str]] = None,
) -> tuple[bool, Optional[str]]:
    """Validate email content.
    
    Args:
        subject: Email subject
        body: Email body
        required_elements: Optional list of required elements
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not subject or not subject.strip():
        return False, "Subject cannot be empty"
    
    if not body or not body.strip():
        return False, "Body cannot be empty"
    
    if len(subject) > 200:
        return False, "Subject too long (max 200 characters)"
    
    if required_elements:
        body_lower = body.lower()
        for element in required_elements:
            if element.lower() not in body_lower:
                return False, f"Required element missing: {element}"
    
    return True, None


def generate_email_subject(
    email_type: str,
    candidate_name: str,
    job_title: str,
    company_name: str,
) -> str:
    """Generate email subject line.
    
    Args:
        email_type: Type of email
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        
    Returns:
        Email subject
    """
    templates = {
        "interview": f"Interview Invitation - {job_title} at {company_name}",
        "rejection": f"Update on your application - {job_title}",
        "offer": f"Job Offer - {job_title} at {company_name}",
        "confirmation": f"Application Received - {job_title}",
        "status_update": f"Application Status Update - {job_title}",
    }
    
    return templates.get(email_type, f"Regarding your application - {company_name}")


def extract_email_intent(email_text: str) -> str:
    """Extract intent from candidate's email response.
    
    Args:
        email_text: Email text from candidate
        
    Returns:
        Intent (accept, decline, reschedule, question)
    """
    email_lower = email_text.lower()
    
    accept_keywords = ["accept", "confirm", "yes", "agree", "sounds good", "looking forward"]
    decline_keywords = ["decline", "no longer interested", "withdraw", "cannot accept"]
    reschedule_keywords = ["reschedule", "different time", "not available", "conflict"]
    
    if any(keyword in email_lower for keyword in accept_keywords):
        return "accept"
    elif any(keyword in email_lower for keyword in decline_keywords):
        return "decline"
    elif any(keyword in email_lower for keyword in reschedule_keywords):
        return "reschedule"
    else:
        return "question"
