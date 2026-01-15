"""Jobs API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path

from api.dependencies import require_active_user
from database.models.users import User
from api.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    department: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search by title"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_active_user),
):
    """List jobs for the organization."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not part of an organization")
    
    result = await job_service.list_jobs(
        organization_id=current_user.organization_id,
        status=status,
        department=department,
        search_query=search,
        limit=limit,
        offset=offset,
    )
    return result


@router.get("/{job_id}")
async def get_job(
    job_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get job details."""
    result = await job_service.get_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.get("/{job_id}/requirements")
async def get_job_requirements(
    job_id: int = Path(...),
    current_user: User = Depends(require_active_user),
):
    """Get structured requirements for a job."""
    result = await job_service.get_job_requirements(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
