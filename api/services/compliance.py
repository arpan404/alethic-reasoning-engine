"""Compliance service functions (GDPR, FCRA, EEO)."""

from typing import Any, Optional
from datetime import datetime
import logging
import uuid

from sqlalchemy import select
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
) -> dict[str, Any]:
    """Generate FCRA-compliant adverse action notice."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application or not application.candidate:
            return {"success": False, "error": "Application not found"}
        
        candidate = application.candidate
        
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
) -> dict[str, Any]:
    """Verify I-9 work authorization."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application or not application.candidate:
            return {"success": False, "error": "Application not found"}
        
        expiry: Optional[datetime] = None
        if expiry_date:
            try:
                expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
            except ValueError:
                pass
        
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


async def export_user_data(user_id: int) -> dict[str, Any]:
    """Export all data for a user (GDPR Article 15)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            cand_result = await session.execute(
                select(Candidate).where(Candidate.id == user_id)
            )
            candidate = cand_result.scalar_one_or_none()
            
            if candidate:
                return await _export_candidate_data(session, candidate)
            
            return {"error": "User not found"}
        
        data: dict[str, Any] = {
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


async def _export_candidate_data(session: Any, candidate: Candidate) -> dict[str, Any]:
    """Export candidate-specific data."""
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


async def erase_user_data(
    user_id: int,
    erased_by: Optional[int] = None,
) -> dict[str, Any]:
    """Erase all user data (GDPR Article 17)."""
    confirmation_id = f"erasure_{uuid.uuid4().hex[:12]}"
    
    async with AsyncSessionLocal() as session:
        cand_result = await session.execute(
            select(Candidate).where(Candidate.id == user_id)
        )
        candidate = cand_result.scalar_one_or_none()
        
        records_deleted = 0
        
        if candidate:
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
) -> dict[str, Any]:
    """Generate EEO report."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}
    
    task_id = f"eeo_report_{uuid.uuid4().hex[:12]}"
    
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
            "report_period": {"start": start_date, "end": end_date},
        }
    except Exception as e:
        logger.error(f"Failed to queue EEO report: {e}")
        return {"success": False, "error": str(e)}
