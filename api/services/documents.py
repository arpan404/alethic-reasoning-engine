"""
Document service functions for API endpoints.

Provides direct database operations for document retrieval,
separate from AI agent tools.
"""

from typing import Any, Dict, Optional
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.applications import Application
from database.models.candidates import Candidate
from database.models.files import File

logger = logging.getLogger(__name__)


async def get_resume(application_id: int) -> Optional[Dict[str, Any]]:
    """
    Get parsed resume data for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with resume data or None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(
                selectinload(Application.files),
                selectinload(Application.candidate),
            )
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return None
        
        # Find resume file
        resume_file = None
        for f in application.files:
            if f.file_type == "resume":
                resume_file = f
                break
        
        if not resume_file:
            return None
        
        # Get parsed data from candidate if available
        candidate = application.candidate
        
        return {
            "application_id": application_id,
            "file_id": resume_file.id,
            "filename": resume_file.original_filename,
            "parsed_data": {
                "contact": {
                    "name": f"{candidate.first_name} {candidate.last_name}" if candidate else None,
                    "email": candidate.email if candidate else None,
                    "phone": candidate.phone if candidate else None,
                    "location": candidate.location if candidate else None,
                },
                "experience": candidate.work_history if candidate else [],
                "education": candidate.education if candidate else [],
                "skills": candidate.skills if candidate else [],
                "summary": candidate.summary if hasattr(candidate, 'summary') and candidate else None,
            },
            "raw_text": resume_file.extracted_text if hasattr(resume_file, 'extracted_text') else None,
            "uploaded_at": resume_file.created_at.isoformat() if resume_file.created_at else None,
        }


async def get_cover_letter(application_id: int) -> Optional[Dict[str, Any]]:
    """
    Get cover letter content for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with cover letter content or None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.files))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return None
        
        # Find cover letter file
        cover_letter = None
        for f in application.files:
            if f.file_type == "cover_letter":
                cover_letter = f
                break
        
        if not cover_letter:
            return {"has_cover_letter": False, "content": None}
        
        return {
            "has_cover_letter": True,
            "application_id": application_id,
            "file_id": cover_letter.id,
            "filename": cover_letter.original_filename,
            "content": cover_letter.extracted_text if hasattr(cover_letter, 'extracted_text') else None,
            "uploaded_at": cover_letter.created_at.isoformat() if cover_letter.created_at else None,
        }


async def get_linkedin_profile(application_id: int) -> Optional[Dict[str, Any]]:
    """
    Get LinkedIn profile data for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with LinkedIn data or None
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.candidate))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application or not application.candidate:
            return None
        
        candidate = application.candidate
        
        if not candidate.linkedin_url:
            return {"has_linkedin": False}
        
        # Return stored LinkedIn data
        linkedin_data = candidate.linkedin_data if hasattr(candidate, 'linkedin_data') else None
        
        return {
            "has_linkedin": True,
            "application_id": application_id,
            "linkedin_url": candidate.linkedin_url,
            "profile_data": linkedin_data or {
                "headline": candidate.current_title,
                "current_company": candidate.current_company,
                "experience_years": candidate.experience_years,
            },
        }


async def get_portfolio(application_id: int) -> Dict[str, Any]:
    """
    Get portfolio items for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with portfolio items
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(
                selectinload(Application.files),
                selectinload(Application.candidate),
            )
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"error": "Application not found"}
        
        items = []
        
        # Get portfolio files
        for f in application.files:
            if f.file_type == "portfolio":
                items.append({
                    "type": "file",
                    "file_id": f.id,
                    "filename": f.original_filename,
                    "uploaded_at": f.created_at.isoformat() if f.created_at else None,
                })
        
        # Get portfolio URL from candidate
        if application.candidate and application.candidate.portfolio_url:
            items.append({
                "type": "url",
                "url": application.candidate.portfolio_url,
            })
        
        return {
            "application_id": application_id,
            "items": items,
            "total": len(items),
        }


async def get_all_documents(application_id: int) -> Dict[str, Any]:
    """
    Get all documents for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary with all documents categorized
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Application)
            .options(selectinload(Application.files))
            .where(Application.id == application_id)
        )
        application = result.scalar_one_or_none()
        
        if not application:
            return {"error": "Application not found"}
        
        documents = {
            "resume": None,
            "cover_letters": [],
            "portfolios": [],
            "other": [],
        }
        
        for f in application.files:
            doc = {
                "id": f.id,
                "filename": f.original_filename,
                "file_type": f.file_type,
                "size_bytes": f.size_bytes,
                "uploaded_at": f.created_at.isoformat() if f.created_at else None,
            }
            
            if f.file_type == "resume":
                documents["resume"] = doc
            elif f.file_type == "cover_letter":
                documents["cover_letters"].append(doc)
            elif f.file_type == "portfolio":
                documents["portfolios"].append(doc)
            else:
                documents["other"].append(doc)
        
        return {
            "application_id": application_id,
            "documents": documents,
        }
