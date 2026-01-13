"""Email context preparation and validation tools for LLM-driven email composition."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def prepare_interview_invitation_context(
    candidate_name: str,
    job_title: str,
    company_name: str,
    interview_date: datetime,
    interview_duration: int,
    interview_type: str,
    interviewer_name: str,
    additional_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prepare context for LLM to generate interview invitation email.
    
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
        Context dictionary for LLM
    """
    context = {
        "email_type": "interview_invitation",
        "candidate_name": candidate_name,
        "job_title": job_title,
        "company_name": company_name,
        "interview_date": interview_date.strftime('%A, %B %d, %Y'),
        "interview_time": interview_date.strftime('%I:%M %p %Z'),
        "interview_duration": interview_duration,
        "interview_type": interview_type,
        "interviewer_name": interviewer_name,
        "tone": "professional and welcoming",
        "key_points": [
            "Express enthusiasm about interviewing the candidate",
            "Provide all interview details clearly",
            "Request confirmation of availability",
            "Mention rescheduling options"
        ]
    }
    
    if additional_details:
        context.update(additional_details)
    
    return context


def prepare_rejection_email_context(
    candidate_name: str,
    job_title: str,
    company_name: str,
    personalized_feedback: Optional[str] = None,
    keep_in_pool: bool = False,
    interview_completed: bool = False,
) -> Dict[str, Any]:
    """Prepare context for LLM to generate rejection email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        personalized_feedback: Optional personalized feedback
        keep_in_pool: Whether to keep in talent pool
        interview_completed: Whether candidate completed interviews
        
    Returns:
        Context dictionary for LLM
    """
    context = {
        "email_type": "rejection",
        "candidate_name": candidate_name,
        "job_title": job_title,
        "company_name": company_name,
        "personalized_feedback": personalized_feedback,
        "keep_in_pool": keep_in_pool,
        "interview_completed": interview_completed,
        "tone": "respectful and empathetic",
        "key_points": [
            "Thank the candidate for their time and interest",
            "Deliver the decision clearly but compassionately",
            "Encourage future applications if appropriate",
            "Maintain positive relationship"
        ]
    }
    
    return context


def prepare_offer_letter_context(
    candidate_name: str,
    job_title: str,
    company_name: str,
    salary: float,
    start_date: datetime,
    benefits: List[str],
    additional_details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prepare context for LLM to generate job offer email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        salary: Annual salary
        start_date: Proposed start date
        benefits: List of benefits
        additional_details: Optional additional details
        
    Returns:
        Context dictionary for LLM
    """
    context = {
        "email_type": "job_offer",
        "candidate_name": candidate_name,
        "job_title": job_title,
        "company_name": company_name,
        "salary": f"${salary:,.2f}",
        "start_date": start_date.strftime('%B %d, %Y'),
        "benefits": benefits,
        "response_deadline": (datetime.now() + timedelta(days=7)).strftime('%B %d, %Y'),
        "tone": "enthusiastic and professional",
        "key_points": [
            "Express excitement about extending the offer",
            "Clearly present compensation and benefits",
            "Provide next steps and deadline",
            "Welcome them to the team"
        ]
    }
    
    if additional_details:
        context.update(additional_details)
    
    return context


def prepare_application_confirmation_context(
    candidate_name: str,
    job_title: str,
    company_name: str,
    next_steps: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare context for LLM to generate application confirmation email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        next_steps: Optional next steps information
        
    Returns:
        Context dictionary for LLM
    """
    context = {
        "email_type": "application_confirmation",
        "candidate_name": candidate_name,
        "job_title": job_title,
        "company_name": company_name,
        "next_steps": next_steps or "We will review your application and contact you within 1-2 weeks.",
        "tone": "friendly and appreciative",
        "key_points": [
            "Acknowledge receipt of application",
            "Thank candidate for their interest",
            "Set expectations for next steps",
            "Encourage engagement with company"
        ]
    }
    
    return context


def prepare_status_update_context(
    candidate_name: str,
    job_title: str,
    company_name: str,
    current_stage: str,
    expected_timeline: Optional[str] = None,
    progress_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare context for LLM to generate status update email.
    
    Args:
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        current_stage: Current stage in process
        expected_timeline: Optional expected timeline
        progress_notes: Optional additional progress information
        
    Returns:
        Context dictionary for LLM
    """
    context = {
        "email_type": "status_update",
        "candidate_name": candidate_name,
        "job_title": job_title,
        "company_name": company_name,
        "current_stage": current_stage,
        "expected_timeline": expected_timeline,
        "progress_notes": progress_notes,
        "tone": "informative and reassuring",
        "key_points": [
            "Provide clear update on application status",
            "Maintain candidate engagement",
            "Set realistic expectations",
            "Show appreciation for patience"
        ]
    }
    
    return context


def create_email_prompt(
    context: Dict[str, Any],
    custom_instructions: Optional[str] = None,
) -> str:
    """Create LLM prompt for email generation.
    
    Args:
        context: Email context dictionary
        custom_instructions: Optional additional instructions
        
    Returns:
        Formatted prompt for LLM
    """
    email_type = context.get("email_type", "email")
    
    prompt = f"""Generate a professional recruiting email with the following details:

Email Type: {email_type}
Candidate Name: {context.get('candidate_name')}
Job Title: {context.get('job_title')}
Company Name: {context.get('company_name')}
Tone: {context.get('tone', 'professional')}

Key Points to Include:
"""
    
    for point in context.get('key_points', []):
        prompt += f"- {point}\n"
    
    prompt += "\nAdditional Context:\n"
    for key, value in context.items():
        if key not in ['email_type', 'candidate_name', 'job_title', 'company_name', 'tone', 'key_points']:
            if isinstance(value, list):
                prompt += f"{key.replace('_', ' ').title()}:\n"
                for item in value:
                    prompt += f"  - {item}\n"
            elif value:
                prompt += f"{key.replace('_', ' ').title()}: {value}\n"
    
    if custom_instructions:
        prompt += f"\nAdditional Instructions:\n{custom_instructions}\n"
    
    prompt += """
Generate the email with:
1. A compelling subject line
2. A professional, personalized email body
3. Appropriate formatting and structure

Return the response in the following JSON format:
{
    "subject": "email subject line",
    "body": "email body text"
}
"""
    
    return prompt


def parse_llm_email_response(
    llm_response: str,
) -> Dict[str, str]:
    """Parse LLM response to extract email content.
    
    Args:
        llm_response: Raw LLM response
        
    Returns:
        Dictionary with subject and body
    """
    import json
    import re
    
    try:
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*"subject"[^{}]*"body"[^{}]*\}', llm_response, re.DOTALL)
        if json_match:
            email_data = json.loads(json_match.group(0))
            return {
                "subject": email_data.get("subject", ""),
                "body": email_data.get("body", "")
            }
        
        # Fallback: try to find subject and body separately
        subject_match = re.search(r'[Ss]ubject:\s*(.+?)(?:\n|$)', llm_response)
        body_match = re.search(r'[Bb]ody:\s*(.+)', llm_response, re.DOTALL)
        
        if subject_match and body_match:
            return {
                "subject": subject_match.group(1).strip(),
                "body": body_match.group(1).strip()
            }
        
        # If no structure found, return as body
        logger.warning("Could not parse structured email from LLM response")
        return {
            "subject": "Application Update",
            "body": llm_response.strip()
        }
    
    except Exception as e:
        logger.error(f"Error parsing LLM email response: {e}")
        return {
            "subject": "Application Update",
            "body": llm_response.strip()
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
    
    if len(body) < 50:
        return False, "Body too short (min 50 characters)"
    
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
    """Generate email subject line (fallback for non-LLM usage).
    
    Args:
        email_type: Type of email
        candidate_name: Name of candidate
        job_title: Job title
        company_name: Company name
        
    Returns:
        Email subject
    """
    templates = {
        "interview_invitation": f"Interview Invitation - {job_title} at {company_name}",
        "rejection": f"Update on your application - {job_title}",
        "job_offer": f"Job Offer - {job_title} at {company_name}",
        "application_confirmation": f"Application Received - {job_title}",
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
    import re
    
    email_lower = email_text.lower()
    
    accept_keywords = ["accept", "confirm", "yes", "agree", "sounds good", "looking forward", "excited"]
    decline_keywords = ["decline", "no longer interested", "withdraw", "cannot accept", "pass", "regret"]
    reschedule_keywords = ["reschedule", "different time", "not available", "conflict", "busy", "another time"]
    question_keywords = ["question", "wondering", "clarify", "could you", "would you", "what", "when", "how"]
    
    # Count keyword matches
    accept_score = sum(1 for kw in accept_keywords if kw in email_lower)
    decline_score = sum(1 for kw in decline_keywords if kw in email_lower)
    reschedule_score = sum(1 for kw in reschedule_keywords if kw in email_lower)
    question_score = sum(1 for kw in question_keywords if kw in email_lower)
    
    # Determine intent based on highest score
    scores = {
        "accept": accept_score,
        "decline": decline_score,
        "reschedule": reschedule_score,
        "question": question_score
    }
    
    max_intent = max(scores, key=scores.get)
    
    # Return intent only if score is meaningful
    if scores[max_intent] > 0:
        return max_intent
    
    return "question"  # Default to question


def enhance_email_with_context(
    base_email: Dict[str, str],
    candidate_data: Dict[str, Any],
    job_data: Dict[str, Any],
) -> Dict[str, str]:
    """Enhance email with additional context about candidate and job.
    
    Args:
        base_email: Base email dict with subject and body
        candidate_data: Candidate information
        job_data: Job information
        
    Returns:
        Enhanced email dictionary
    """
    # This could be used to add personalization based on candidate profile
    # For example, mentioning specific skills or experiences
    
    enhanced = base_email.copy()
    
    # Add personalization opportunities
    skills_match = candidate_data.get("matched_skills", [])
    if skills_match:
        skills_text = ", ".join(skills_match[:3])
        enhanced["personalization_notes"] = f"Candidate has relevant skills: {skills_text}"
    
    return enhanced


def prepare_email_metadata(
    candidate_id: str,
    job_id: str,
    email_type: str,
    priority: str = "normal",
) -> Dict[str, Any]:
    """Prepare metadata for email tracking.
    
    Args:
        candidate_id: ID of candidate
        job_id: ID of job
        email_type: Type of email
        priority: Email priority
        
    Returns:
        Metadata dictionary
    """
    return {
        "candidate_id": candidate_id,
        "job_id": job_id,
        "email_type": email_type,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "requires_response": email_type in ["interview_invitation", "job_offer"],
    }

