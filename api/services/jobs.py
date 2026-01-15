"""Job service functions."""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.jobs import Job, JobStatus, JobRequirement
from database.models.applications import Application

logger = logging.getLogger(__name__)


async def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Get job details."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        count_result = await session.execute(
            select(func.count())
            .select_from(Application)
            .where(Application.job_id == job_id)
        )
        application_count = count_result.scalar() or 0
        
        return {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "location": job.location,
            "employment_type": job.employment_type,
            "experience_level": job.experience_level,
            "description": job.description,
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "is_remote": job.is_remote,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "published_at": job.published_at.isoformat() if job.published_at else None,
            "closes_at": job.closes_at.isoformat() if job.closes_at else None,
            "organization_id": job.organization_id,
            "application_count": application_count,
        }


async def list_jobs(
    organization_id: int,
    status: Optional[str] = None,
    department: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List jobs for an organization."""
    async with AsyncSessionLocal() as session:
        query = select(Job).where(Job.organization_id == organization_id)
        
        if status:
            try:
                status_enum = JobStatus(status)
                query = query.where(Job.status == status_enum)
            except ValueError:
                pass
                
        if department:
            query = query.where(Job.department == department)
            
        if search_query:
            query = query.where(Job.title.ilike(f"%{search_query}%"))
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(Job.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await session.execute(query)
        jobs = result.scalars().all()
        
        job_list = []
        for job in jobs:
            count_result = await session.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.job_id == job.id)
            )
            app_count = count_result.scalar() or 0
            
            job_list.append({
                "id": job.id,
                "title": job.title,
                "department": job.department,
                "location": job.location,
                "employment_type": job.employment_type,
                "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
                "is_remote": job.is_remote,
                "application_count": app_count,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            })
        
        return {
            "jobs": job_list,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


async def get_job_requirements(job_id: int) -> Dict[str, Any]:
    """Get job requirements."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return {"error": "Job not found"}
        
        requirements = {
            "job_id": job.id,
            "job_title": job.title,
            "required_skills": [],
            "preferred_skills": [],
            "experience_min_years": job.experience_min_years if hasattr(job, 'experience_min_years') else None,
            "experience_max_years": job.experience_max_years if hasattr(job, 'experience_max_years') else None,
            "education_level": job.education_level if hasattr(job, 'education_level') else None,
            "certifications": [],
            "qualifications": job.qualifications,
        }
        
        for req in job.requirements:
            req_data = {
                "name": req.name if hasattr(req, 'name') else str(req),
                "is_required": req.is_required if hasattr(req, 'is_required') else True,
                "importance": req.importance if hasattr(req, 'importance') else "medium",
            }
            
            if req_data["is_required"]:
                requirements["required_skills"].append(req_data)
            else:
                requirements["preferred_skills"].append(req_data)
        
        return requirements
