"""
Compliance service functions for API endpoints.

Provides direct database operations for compliance (GDPR, FCRA, EEO),
separate from AI agent tools.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application
from database.models.candidates import Candidate
from database.models.users import User
from database.models.compliance import AdverseActionNotice, WorkAuthorization
from database.models.audit import AuditLog

logger = logging.getLogger(__name__)


async def generate_adverse_action_notice(
    application_id: int,
    reason: str,
    notice_type: str = "pre",
    generated_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate FCRA-compliant adverse action notice.
    
    Args:
        application_id: The application this notice is for
        reason: Reason for adverse action
        notice_type: Type of notice ('pre' or 'final')
        generated_by: User ID who generated
        
    Returns:
        Dictionary with notice details
    """
    async with AsyncSessionLocal() as session:
        # Get application and candidate
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application or not application.candidate:
            return {"success": False, "error": "Application not found"}
        
        candidate = application.candidate
        
        # Create adverse action notice
        notice = AdverseActionNotice(
            application_id=application_id,
            candidate_id=candidate.id,
            notice_type=notice_type,
            reason=reason,
            generated_by_id=generated_by,
            status="generated",
        )
        session.add(notice)
        await session.flush()
        
        # Generate notice content
        notice_content = {
            "notice_id": notice.id,
            "type": notice_type,
            "candidate_name": f"{candidate.first_name} {candidate.last_name}",
            "candidate_email": candidate.email,
            "reason": reason,
            "generated_at": datetime.utcnow().isoformat(),
            "required_wait_period": "5 business days" if notice_type == "pre" else None,
            "consumer_rights": [
                "Right to obtain a free copy of the consumer report",
                "Right to dispute the accuracy of the report",
                "Right to a description of consumer rights",
            ],
            "agency_contact": {
                "name": "Consumer Reporting Agency",
                "address": "Address on file",
                "phone": "Phone on file",
            },
        }
        
        await session.commit()
        
        return {
            "success": True,
            "notice_id": notice.id,
            "notice_type": notice_type,
            "content": notice_content,
            "status": "generated",
        }


async def verify_work_authorization(
    application_id: int,
    document_type: str,
    document_number: Optional[str] = None,
    expiry_date: Optional[str] = None,
    verified_by: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Verify I-9 work authorization for a candidate.
    
    Args:
        application_id: The application to verify
        document_type: Type of document
        document_number: Document ID number
        expiry_date: Document expiration date
        verified_by: User ID who verified
        
    Returns:
        Dictionary with verification status
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application or not application.candidate:
            return {"success": False, "error": "Application not found"}
        
        # Parse expiry date
        expiry = None
        if expiry_date:
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
            except ValueError:
                pass
        
        # Create work authorization record
        authorization = WorkAuthorization(
            application_id=application_id,
            candidate_id=application.candidate_id,
            document_type=document_type,
            document_number=document_number,
            expiry_date=expiry,
            verified_by_id=verified_by,
            status="pending_verification",
        )
        session.add(authorization)
        await session.flush()
        
        await session.commit()
        
        # Queue E-Verify check if applicable
        try:
            from workers.tasks import queue_everify_check
            await queue_everify_check(authorization.id)
        except Exception as e:
            logger.warning(f"Failed to queue E-Verify check: {e}")
        
        return {
            "success": True,
            "authorization_id": authorization.id,
            "application_id": application_id,
            "document_type": document_type,
            "status": "pending_verification",
        }


async def export_user_data(user_id: int) -> Dict[str, Any]:
    """
    Export all data for a user (GDPR Article 15).
    
    Args:
        user_id: The user ID to export data for
        
    Returns:
        Dictionary with all user data
    """
    async with AsyncSessionLocal() as session:
        # Get user
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Check if it's a candidate
            cand_result = await session.execute(
                select(Candidate).where(Candidate.id == user_id)
            )
            candidate = cand_result.scalar_one_or_none()
            
            if candidate:
                return await _export_candidate_data(session, candidate)
            
            return {"error": "User not found"}
        
        # Compile user data
        data = {
            "export_date": datetime.utcnow().isoformat(),
            "export_type": "GDPR_DSAR",
            "profile": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "activity_logs": [],
            "format": "JSON",
        }
        
        # Get audit logs for user
        audit_result = await session.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(1000)
        )
        audits = audit_result.scalars().all()
        
        data["activity_logs"] = [
            {
                "action": log.action,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "details": log.details,
            }
            for log in audits
        ]
        
        return data


async def _export_candidate_data(session, candidate: Candidate) -> Dict[str, Any]:
    """Export candidate-specific data."""
    # Get applications
    app_result = await session.execute(
        select(Application).where(Application.candidate_id == candidate.id)
    )
    applications = app_result.scalars().all()
    
    return {
        "export_date": datetime.utcnow().isoformat(),
        "export_type": "GDPR_DSAR",
        "profile": {
            "id": candidate.id,
            "email": candidate.email,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "phone": candidate.phone,
            "location": candidate.location,
        },
        "applications": [
            {
                "id": app.id,
                "job_id": app.job_id,
                "status": app.status,
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            }
            for app in applications
        ],
        "format": "JSON",
    }


async def erase_user_data(user_id: int, erased_by: Optional[int] = None) -> Dict[str, Any]:
    """
    Erase all user data (GDPR Article 17).
    
    Args:
        user_id: The user ID to erase data for
        erased_by: User ID who initiated erasure
        
    Returns:
        Dictionary with erasure confirmation
    """
    confirmation_id = f"erasure_{uuid.uuid4().hex[:12]}"
    
    async with AsyncSessionLocal() as session:
        # Check if candidate
        cand_result = await session.execute(
            select(Candidate).where(Candidate.id == user_id)
        )
        candidate = cand_result.scalar_one_or_none()
        
        records_deleted = 0
        
        if candidate:
            # Anonymize candidate data instead of hard delete
            candidate.first_name = "REDACTED"
            candidate.last_name = "REDACTED"
            candidate.email = f"redacted_{candidate.id}@deleted.local"
            candidate.phone = None
            candidate.location = None
            candidate.linkedin_url = None
            candidate.portfolio_url = None
            candidate.skills = []
            candidate.education = []
            candidate.work_history = []
            records_deleted += 1
            
            await session.commit()
        
        # Log the erasure
        audit = AuditLog(
            user_id=erased_by,
            action="data_erasure",
            resource_type="candidate",
            resource_id=user_id,
            details={"confirmation_id": confirmation_id},
        )
        session.add(audit)
        await session.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "records_deleted": records_deleted,
            "confirmation_id": confirmation_id,
            "erased_at": datetime.utcnow().isoformat(),
        }


async def generate_eeo_report(
    start_date: str,
    end_date: str,
    job_id: Optional[int] = None,
    organization_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate EEO (Equal Employment Opportunity) report.
    
    Args:
        start_date: Report start date (YYYY-MM-DD)
        end_date: Report end date (YYYY-MM-DD)
        job_id: Optional filter by job
        organization_id: Organization ID
        
    Returns:
        Dictionary with report data or task ID
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    task_id = f"eeo_report_{uuid.uuid4().hex[:12]}"
    
    # Queue report generation
    try:
        from workers.tasks import queue_eeo_report
        await queue_eeo_report(
            task_id=task_id,
            start_date=start,
            end_date=end,
            job_id=job_id,
            organization_id=organization_id,
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "report_period": {
                "start": start_date,
                "end": end_date,
            },
        }
    except Exception as e:
        logger.error(f"Failed to queue EEO report: {e}")
        return {"success": False, "error": str(e)}
