"""
Job posting management endpoints.

Provides REST API for listing and viewing job postings and their requirements.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from api.dependencies import require_active_user
from database.models.users import User
from core.middleware.authorization import Permission, require_permission
from api.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "",
    summary="List Jobs",
    description="List job postings for the organization. Requires job:read permission.",
    dependencies=[Depends(require_permission(Permission.JOB_READ))],
)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status (open, closed, draft)"),
    department: Optional[str] = Query(None, description="Filter by department"),
    search: Optional[str] = Query(None, description="Search by title"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """Retrieve a paginated list of job postings for the organization."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    return await job_service.list_jobs(
        organization_id=current_user.organization_id,
        status=status,
        department=department,
        search_query=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}",
    summary="Get Job Details",
    description="Get detailed information about a job posting. Requires job:read permission.",
    dependencies=[Depends(require_permission(Permission.JOB_READ))],
)
async def get_job(
    job_id: int = Path(..., description="Job ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve complete job posting details including description and requirements."""
    result = await job_service.get_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.get(
    "/{job_id}/requirements",
    summary="Get Job Requirements",
    description="Get structured requirements for a job. Requires job:read permission.",
    dependencies=[Depends(require_permission(Permission.JOB_READ))],
)
async def get_job_requirements(
    job_id: int = Path(..., description="Job ID"),
    current_user: User = Depends(require_active_user),
):
    """Retrieve structured skills and qualification requirements for matching."""
    result = await job_service.get_job_requirements(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
