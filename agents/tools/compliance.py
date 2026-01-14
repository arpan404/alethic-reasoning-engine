"""Compliance tools for Alethic agents.

These tools handle legally-required documents and compliance checks
that have specific regulatory requirements (FCRA, EEO, I-9).
Only tools that require specific legal formatting are included here.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application
from database.models.candidates import Candidate
from agents.tools.queue import enqueue_task

logger = logging.getLogger(__name__)


async def generate_adverse_action_notice(
    application_id: int,
    notice_type: str,
    background_check_id: Optional[str] = None,
    reasons: Optional[List[str]] = None,
    generated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate FCRA-compliant adverse action notice.
    
    Multi-tenant safe: Operates through application context.
    
    This creates legally-required notices when taking adverse action
    based on background check results or credit reports.
    
    Args:
        application_id: The application ID
        notice_type: Type of notice (pre_adverse, adverse)
        background_check_id: Related background check ID
        reasons: Specific reasons for adverse action
        generated_by: User ID who generated
        
    Returns:
        Dictionary with generated notice details
    """
    valid_types = ["pre_adverse", "adverse"]
    if notice_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid notice type '{notice_type}'. Valid types: {valid_types}",
        }
    
    
    async with AsyncSessionLocal() as session:
        query = (
            select(Application)
            .options(selectinload(Application.candidate), selectinload(Application.job))
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application {application_id} not found",
            }
        
        candidate = app.candidate
        job = app.job
        
        if not candidate:
            return {
                "success": False,
                "error": "Candidate not found",
            }
        
        candidate_name = f"{candidate.first_name} {candidate.last_name}".strip()
        job_title = job.title if job else "the position"
    
    # Queue the notice generation
    task_result = await enqueue_task(
        task_type="generate_adverse_action_notice",
        payload={
            "application_id": application_id,
            "candidate_id": candidate.id,
            "notice_type": notice_type,
            "background_check_id": background_check_id,
            "reasons": reasons or [],
            "candidate_name": candidate_name,
            "job_title": job_title,
            "generated_by": generated_by,
        },
        priority="high",
    )
    
    logger.info(
        f"Generated {notice_type} adverse action notice for application {application_id}"
    )
    
    return {
        "success": True,
        "notice_type": notice_type,
        "application_id": application_id,
        "candidate_name": candidate_name,
        "task_id": task_result.get("task_id"),
        "message": f"{notice_type.replace('_', '-').title()} notice generation queued",
        "required_actions": [
            "Notice must be sent to candidate before adverse action",
            "Candidate must be given copy of background check report",
            "Candidate must be provided summary of rights under FCRA",
        ] if notice_type == "pre_adverse" else [
            "Document adverse action decision",
            "Retain records for compliance period",
        ],
    }


async def verify_work_authorization(
    application_id: int,
    document_type: str,
    document_number: str,
    expiration_date: Optional[datetime] = None,
    verified_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Verify I-9 work authorization status.
    
    Multi-tenant safe: Operates through application context.
    Initiates verification with E-Verify or similar system.
    
    Args:
        application_id: The application ID
        document_type: Type of document (passport, visa, green_card, etc.)
        document_number: Document number
        expiration_date: Document expiration date if applicable
        verified_by: User ID who verified
        
    Returns:
        Dictionary with verification status
    """
    valid_documents = [
        "us_passport",
        "permanent_resident_card", 
        "employment_authorization_document",
        "foreign_passport_with_i94",
        "drivers_license_with_ssn_card",
        "state_id_with_ssn_card",
        "birth_certificate_with_ssn_card",
    ]
    
    if document_type not in valid_documents:
        return {
            "success": False,
            "error": f"Invalid document type. Valid types: {valid_documents}",
        }
    
    # Get candidate_id from application
    async with AsyncSessionLocal() as session:
        query = select(Application).where(Application.id == application_id)
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return {
                "success": False,
                "error": f"Application {application_id} not found",
            }
        
        candidate_id = app.candidate_id
    
    # Queue the verification
    task_result = await enqueue_task(
        task_type="verify_work_authorization",
        payload={
            "application_id": application_id,
            "candidate_id": candidate_id,
            "document_type": document_type,
            "document_number": document_number,
            "expiration_date": expiration_date.isoformat() if expiration_date else None,
            "verified_by": verified_by,
        },
        priority="high",
    )
    
    logger.info(
        f"Initiated work authorization verification for application {application_id}"
    )
    
    return {
        "success": True,
        "application_id": application_id,
        "document_type": document_type,
        "task_id": task_result.get("task_id"),
        "status": "verification_initiated",
        "message": "Work authorization verification initiated. Results typically available within 24 hours.",
    }


async def generate_eeo_report(
    organization_id: int,
    job_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    report_type: str = "eeo1",
) -> Dict[str, Any]:
    """Generate EEO-1 compliance report.
    
    Creates required equal employment opportunity reports
    for regulatory compliance.
    
    Args:
        organization_id: The organization ID
        job_id: Optional filter by job
        start_date: Report start date
        end_date: Report end date
        report_type: Type of report (eeo1, vets4212, etc.)
        
    Returns:
        Dictionary with report generation status
    """
    valid_report_types = ["eeo1", "vets4212", "aap"]
    if report_type not in valid_report_types:
        return {
            "success": False,
            "error": f"Invalid report type. Valid types: {valid_report_types}",
        }
    
    # Queue the report generation
    task_result = await enqueue_task(
        task_type="generate_eeo_report",
        payload={
            "organization_id": organization_id,
            "job_id": job_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "report_type": report_type,
        },
        priority="normal",
    )
    
    logger.info(
        f"Queued {report_type} report generation for organization {organization_id}"
    )
    
    return {
        "success": True,
        "organization_id": organization_id,
        "report_type": report_type,
        "task_id": task_result.get("task_id"),
        "message": f"{report_type.upper()} report generation queued",
    }
