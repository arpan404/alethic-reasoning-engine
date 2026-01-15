"""Communications service functions."""

from typing import Any, Optional
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.communications import EmailTemplate, CommunicationLog
from database.models.applications import Application

logger = logging.getLogger(__name__)


async def send_email(
    application_id: int,
    template_id: Optional[int] = None,
    custom_subject: Optional[str] = None,
    custom_content: Optional[str] = None,
    sent_by: Optional[int] = None,
) -> dict[str, Any]:
    """Send an email to a candidate."""
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
        
        subject = custom_subject
        content = custom_content
        
        if template_id:
            tmpl_result = await session.execute(
                select(EmailTemplate).where(EmailTemplate.id == template_id)
            )
            template = tmpl_result.scalar_one_or_none()
            
            if template:
                subject = subject or template.subject
                content = content or template.content
                
                placeholders: dict[str, str] = {
                    "{{candidate_name}}": f"{candidate.first_name} {candidate.last_name}",
                    "{{first_name}}": candidate.first_name,
                    "{{last_name}}": candidate.last_name,
                }
                
                for key, value in placeholders.items():
                    if subject:
                        subject = subject.replace(key, value)
                    if content:
                        content = content.replace(key, value)
        
        if not subject or not content:
            return {"success": False, "error": "Subject and content are required"}
        
        log = CommunicationLog(
            application_id=application_id,
            candidate_id=candidate.id,
            type="email",
            subject=subject,
            content=content,
            sent_by_id=sent_by,
            status="queued",
        )
        session.add(log)
        await session.flush()
        
        await session.commit()
        
        try:
            from workers.tasks import queue_email
            await queue_email(
                log_id=log.id,
                to_email=candidate.email,
                subject=subject,
                content=content,
            )
            status = "queued"
        except Exception as e:
            logger.warning(f"Failed to queue email: {e}")
            status = "failed"
        
        return {
            "success": True,
            "communication_id": log.id,
            "recipient": candidate.email,
            "subject": subject,
            "status": status,
        }


async def get_email_templates(
    organization_id: int,
    template_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get available email templates."""
    async with AsyncSessionLocal() as session:
        query = select(EmailTemplate).where(
            EmailTemplate.organization_id == organization_id
        )
        
        if template_type:
            query = query.where(EmailTemplate.type == template_type)
        
        system_query = select(EmailTemplate).where(EmailTemplate.is_system == True)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(EmailTemplate.name)
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        templates = result.scalars().all()
        
        system_result = await session.execute(system_query)
        system_templates = system_result.scalars().all()
        
        all_templates = list(templates) + [t for t in system_templates if t not in templates]
        
        template_list: list[dict[str, Any]] = []
        for tmpl in all_templates:
            template_list.append({
                "id": tmpl.id,
                "name": tmpl.name,
                "type": tmpl.type,
                "subject": tmpl.subject,
                "is_system": tmpl.is_system if hasattr(tmpl, 'is_system') else False,
                "created_at": tmpl.created_at.isoformat() if tmpl.created_at else None,
            })
        
        return {
            "templates": template_list,
            "total": len(template_list),
            "limit": limit,
            "offset": offset,
        }


async def get_communication_history(
    application_id: int,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Get communication history for an application."""
    async with AsyncSessionLocal() as session:
        query = (
            select(CommunicationLog)
            .where(CommunicationLog.application_id == application_id)
        )
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(CommunicationLog.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        communications = result.scalars().all()
        
        comm_list: list[dict[str, Any]] = []
        for comm in communications:
            comm_list.append({
                "id": comm.id,
                "type": comm.type,
                "subject": comm.subject,
                "status": comm.status,
                "sent_by": comm.sent_by_id,
                "sent_at": comm.sent_at.isoformat() if hasattr(comm, 'sent_at') and comm.sent_at else None,
                "created_at": comm.created_at.isoformat() if comm.created_at else None,
                "opened_at": comm.opened_at.isoformat() if hasattr(comm, 'opened_at') and comm.opened_at else None,
            })
        
        return {
            "application_id": application_id,
            "communications": comm_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
