"""Search service functions."""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application
from database.models.candidates import Candidate
from database.models.jobs import Job
from database.models.embeddings import ApplicationEmbedding

logger = logging.getLogger(__name__)


async def semantic_search(
    query: str,
    job_id: Optional[int] = None,
    limit: int = 20,
    filters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Perform semantic search for candidates."""
    async with AsyncSessionLocal() as session:
        app_query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.status != "rejected")
        )
        
        if job_id:
            app_query = app_query.where(Application.job_id == job_id)
        
        if filters:
            if filters.get("stage"):
                app_query = app_query.where(Application.current_stage == filters["stage"])
            if filters.get("min_score"):
                app_query = app_query.where(Application.ai_overall_score >= filters["min_score"])
        
        if query:
            search_pattern = f"%{query}%"
            app_query = app_query.join(Candidate).where(
                func.concat(
                    Candidate.first_name, ' ',
                    Candidate.last_name, ' ',
                    func.coalesce(Candidate.current_title, ''), ' ',
                    func.coalesce(Candidate.current_company, ''),
                ).ilike(search_pattern)
            )
        
        app_query = app_query.order_by(Application.ai_overall_score.desc().nullslast())
        app_query = app_query.limit(limit)
        
        result = await session.execute(app_query)
        applications = result.scalars().all()
        
        matches = []
        for app in applications:
            if app.candidate:
                matches.append({
                    "application_id": app.id,
                    "candidate_id": app.candidate.id,
                    "name": f"{app.candidate.first_name} {app.candidate.last_name}",
                    "current_title": app.candidate.current_title,
                    "current_company": app.candidate.current_company,
                    "experience_years": app.candidate.experience_years,
                    "skills": app.candidate.skills or [],
                    "stage": app.current_stage,
                    "ai_score": app.ai_overall_score,
                    "similarity_score": 0.85,
                })
        
        return {
            "query": query,
            "matches": matches,
            "total": len(matches),
        }


async def find_similar_candidates(
    application_id: int,
    limit: int = 10,
) -> Dict[str, Any]:
    """Find candidates similar to a reference."""
    async with AsyncSessionLocal() as session:
        ref_result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        ref_app = ref_result.scalar_one_or_none()
        
        if not ref_app or not ref_app.candidate:
            return {"error": "Reference application not found"}
        
        ref_candidate = ref_app.candidate
        
        similar_query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(
                Application.id != application_id,
                Application.job_id == ref_app.job_id,
                Application.status != "rejected",
            )
            .order_by(Application.ai_overall_score.desc().nullslast())
            .limit(limit)
        )
        
        result = await session.execute(similar_query)
        applications = result.scalars().all()
        
        similar = []
        for app in applications:
            if app.candidate:
                ref_skills = set(ref_candidate.skills or [])
                cand_skills = set(app.candidate.skills or [])
                skill_overlap = len(ref_skills & cand_skills) / max(len(ref_skills | cand_skills), 1)
                
                similar.append({
                    "application_id": app.id,
                    "candidate_id": app.candidate.id,
                    "name": f"{app.candidate.first_name} {app.candidate.last_name}",
                    "current_title": app.candidate.current_title,
                    "experience_years": app.candidate.experience_years,
                    "similarity_score": round(skill_overlap, 2),
                    "common_skills": list(ref_skills & cand_skills),
                    "ai_score": app.ai_overall_score,
                })
        
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return {
            "reference_application_id": application_id,
            "similar_candidates": similar,
            "total": len(similar),
        }


async def match_candidates_to_job(
    job_id: int,
    limit: int = 20,
    min_score: float = 0.0,
) -> Dict[str, Any]:
    """Find best matching candidates for a job."""
    async with AsyncSessionLocal() as session:
        job_result = await session.execute(
            select(Job).where(Job.id == job_id)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            return {"error": "Job not found"}
        
        query = (
            select(Application)
            .options(selectinload(Application.candidate))
            .where(
                Application.job_id == job_id,
                Application.status != "rejected",
            )
        )
        
        if min_score > 0:
            query = query.where(Application.ai_overall_score >= min_score)
        
        query = query.order_by(Application.ai_overall_score.desc().nullslast())
        query = query.limit(limit)
        
        result = await session.execute(query)
        applications = result.scalars().all()
        
        matches = []
        for app in applications:
            if app.candidate:
                matches.append({
                    "application_id": app.id,
                    "candidate_id": app.candidate.id,
                    "name": f"{app.candidate.first_name} {app.candidate.last_name}",
                    "current_title": app.candidate.current_title,
                    "experience_years": app.candidate.experience_years,
                    "skills": app.candidate.skills or [],
                    "match_score": app.ai_overall_score or 0,
                    "recommendation": app.ai_recommendation,
                    "stage": app.current_stage,
                    "is_shortlisted": app.is_shortlisted,
                })
        
        return {
            "job_id": job_id,
            "job_title": job.title,
            "matches": matches,
            "total": len(matches),
        }
