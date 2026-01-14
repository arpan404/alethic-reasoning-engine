"""Job management tools for Alethic agents.

These tools provide database operations for managing jobs,
including retrieval, listing, and requirement extraction.
"""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.jobs import Job, JobStatus, JobRequirement, HiringTeamMember

logger = logging.getLogger(__name__)


async def get_job(job_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a job.
    
    Args:
        job_id: The unique identifier of the job
        
    Returns:
        Dictionary containing job details, or None if not found
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Job)
            .options(
                selectinload(Job.requirements),
                selectinload(Job.locations),
                selectinload(Job.hiring_team),
                selectinload(Job.department),
            )
            .where(Job.id == job_id)
        )
        result = await session.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            return None
        
        return {
            "id": job.id,
            "title": job.title,
            "slug": job.slug,
            "status": job.status,
            "job_type": job.job_type,
            "visibility": job.visibility,
            "description": job.description,
            "responsibilities": job.responsibilities,
            "qualifications": job.qualifications,
            "benefits": job.benefits,
            "department": job.department.name if job.department else None,
            "locations": [
                {
                    "city": loc.city,
                    "state": loc.state,
                    "country": loc.country,
                    "location_type": loc.location_type,
                    "is_primary": loc.is_primary,
                }
                for loc in (job.locations or [])
            ],
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "experience_min_years": job.experience_min_years,
            "experience_max_years": job.experience_max_years,
            "education_level": job.education_level,
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "hiring_team": [
                {
                    "user_id": member.user_id,
                    "role": member.role,
                    "is_primary": member.is_primary,
                }
                for member in (job.hiring_team or [])
            ],
            "application_count": job.application_count,
            "opens_at": job.opens_at.isoformat() if job.opens_at else None,
            "closes_at": job.closes_at.isoformat() if job.closes_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            # AI Settings
            "ai_screening_enabled": job.ai_screening_enabled,
            "ai_prescreening_enabled": job.ai_prescreening_enabled,
            "ai_prescreening_rounds": job.ai_prescreening_rounds,
            "ideal_candidate_description": job.ideal_candidate_description,
        }


async def list_jobs(
    organization_id: int,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    job_type: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List jobs with optional filtering.
    
    Args:
        organization_id: Filter by organization
        status: Filter by job status (draft, open, paused, closed, filled, archived)
        department_id: Filter by department
        job_type: Filter by job type (full_time, part_time, contract, etc.)
        search_query: Search by title or description
        limit: Maximum number of results
        offset: Number of results to skip
        
    Returns:
        Dictionary with jobs list and pagination info
    """
    async with AsyncSessionLocal() as session:
        query = select(Job).where(Job.organization_id == organization_id)
        conditions = []
        
        # Filter by status
        if status:
            conditions.append(Job.status == status)
        
        # Filter by department
        if department_id:
            conditions.append(Job.department_id == department_id)
        
        # Filter by job type
        if job_type:
            conditions.append(Job.job_type == job_type)
        
        # Search by title or description
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(
                or_(
                    Job.title.ilike(search_pattern),
                    Job.description.ilike(search_pattern),
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar()
        
        # Order by created_at descending and apply pagination
        query = query.order_by(Job.created_at.desc()).offset(offset).limit(limit)
        
        result = await session.execute(query)
        jobs = result.scalars().all()
        
        return {
            "jobs": [
                {
                    "id": j.id,
                    "title": j.title,
                    "slug": j.slug,
                    "status": j.status,
                    "job_type": j.job_type,
                    "department_id": j.department_id,
                    "application_count": j.application_count,
                    "salary_min": j.salary_min,
                    "salary_max": j.salary_max,
                    "experience_min_years": j.experience_min_years,
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                    "opens_at": j.opens_at.isoformat() if j.opens_at else None,
                    "closes_at": j.closes_at.isoformat() if j.closes_at else None,
                }
                for j in jobs
            ],
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(jobs)) < total_count,
        }


async def get_job_requirements(job_id: int) -> Dict[str, Any]:
    """Get detailed requirements for a job.
    
    This provides structured data about what the job requires,
    which is useful for candidate matching and evaluation.
    
    Args:
        job_id: The job ID
        
    Returns:
        Dictionary with structured requirements data
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.id == job_id)
        )
        result = await session.execute(query)
        job = result.scalar_one_or_none()
        
        if not job:
            return {
                "success": False,
                "error": f"Job with ID {job_id} not found",
            }
        
        # Categorize requirements
        requirements_by_type = {}
        for req in (job.requirements or []):
            req_type = req.requirement_type or "other"
            if req_type not in requirements_by_type:
                requirements_by_type[req_type] = []
            requirements_by_type[req_type].append({
                "name": req.name,
                "description": req.description,
                "is_required": req.is_required,
                "proficiency_level": req.proficiency_level,
                "years_required": req.years_required,
            })
        
        return {
            "job_id": job_id,
            "title": job.title,
            "requirements": {
                "skills": {
                    "required": job.required_skills or [],
                    "preferred": job.preferred_skills or [],
                },
                "experience": {
                    "min_years": job.experience_min_years,
                    "max_years": job.experience_max_years,
                    "preferred_industries": job.preferred_industries or [],
                },
                "education": {
                    "level": job.education_level,
                    "preferred_fields": job.preferred_education_fields or [],
                },
                "languages": job.required_languages or [],
                "certifications": job.required_certifications or [],
                "clearance": job.security_clearance_required,
                "work_authorization": job.work_authorization_required,
                "detailed_requirements": requirements_by_type,
            },
            "ideal_candidate_description": job.ideal_candidate_description,
            "evaluation_criteria": job.evaluation_criteria or {},
        }
