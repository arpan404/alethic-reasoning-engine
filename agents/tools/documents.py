"""Document reading tools for Alethic agents.

These tools provide access to parsed document content (resumes, cover letters,
LinkedIn profiles, portfolios) for AI analysis and decision-making.
"""

from typing import Any, Dict, List, Optional
import logging

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from database.engine import AsyncSessionLocal
from database.models.candidates import Candidate
from database.models.applications import Application
from database.models.files import File, ParsedResume

logger = logging.getLogger(__name__)


async def read_resume(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Read the parsed resume data for a candidate.
    
    Returns structured resume data that has been extracted
    from the candidate's uploaded resume file.
    
    Args:
        candidate_id: The candidate ID
        
    Returns:
        Dictionary containing parsed resume data, or None if not found
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Candidate)
            .options(
                selectinload(Candidate.resume_file),
                selectinload(Candidate.education),
                selectinload(Candidate.experience),
            )
            .where(Candidate.id == candidate_id)
        )
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return None
        
        # Get parsed resume if available
        parsed_data = None
        if candidate.resume_file:
            parsed_query = select(ParsedResume).where(
                ParsedResume.file_id == candidate.resume_file.id
            )
            parsed_result = await session.execute(parsed_query)
            parsed = parsed_result.scalar_one_or_none()
            
            if parsed:
                parsed_data = {
                    "raw_text": parsed.raw_text,
                    "structured_data": parsed.structured_data,
                    "parsed_at": parsed.created_at.isoformat() if parsed.created_at else None,
                }
        
        return {
            "candidate_id": candidate_id,
            "name": f"{candidate.first_name} {candidate.last_name}".strip(),
            # Contact info
            "contact": {
                "email": candidate.email,
                "phone": candidate.phone,
                "location": candidate.location,
                "linkedin_url": candidate.linkedin_url,
                "github_url": candidate.github_url,
                "portfolio_url": candidate.portfolio_url,
            },
            # Professional summary
            "headline": candidate.headline,
            "summary": candidate.summary,
            # Experience overview
            "experience_level": candidate.experience_level,
            "years_of_experience": candidate.years_of_experience,
            # Skills
            "skills": candidate.skills or [],
            "languages": candidate.languages or [],
            # Education
            "education_level": candidate.education_level,
            "education": [
                {
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study,
                    "start_date": edu.start_date.isoformat() if edu.start_date else None,
                    "end_date": edu.end_date.isoformat() if edu.end_date else None,
                    "gpa": edu.gpa,
                    "honors": edu.honors,
                    "activities": edu.activities,
                }
                for edu in (candidate.education or [])
            ],
            # Work experience
            "experience": [
                {
                    "company": exp.company,
                    "title": exp.title,
                    "location": exp.location,
                    "employment_type": exp.employment_type,
                    "start_date": exp.start_date.isoformat() if exp.start_date else None,
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "is_current": exp.is_current,
                    "description": exp.description,
                    "achievements": exp.achievements or [],
                }
                for exp in (candidate.experience or [])
            ],
            # Certifications
            "certifications": candidate.certifications or [],
            # Work authorization
            "work_authorization": candidate.work_authorization,
            # Salary expectations
            "salary_expectation": {
                "min": candidate.salary_expectation_min,
                "max": candidate.salary_expectation_max,
                "currency": candidate.salary_currency,
            },
            # Parsed resume data (if available)
            "parsed_resume": parsed_data,
        }


async def read_cover_letter(
    application_id: int,
) -> Optional[Dict[str, Any]]:
    """Read the cover letter for an application.
    
    Args:
        application_id: The application ID
        
    Returns:
        Dictionary containing cover letter content, or None if not found
    """
    async with AsyncSessionLocal() as session:
        # Get application with files
        query = (
            select(Application)
            .options(selectinload(Application.files))
            .where(Application.id == application_id)
        )
        result = await session.execute(query)
        app = result.scalar_one_or_none()
        
        if not app:
            return None
        
        # Find cover letter file
        cover_letter_file = None
        for file in (app.files or []):
            if file.file_type == "cover_letter":
                cover_letter_file = file
                break
        
        if not cover_letter_file:
            return {
                "application_id": application_id,
                "has_cover_letter": False,
                "content": None,
            }
        
        # Get parsed content
        parsed_query = select(ParsedResume).where(
            ParsedResume.file_id == cover_letter_file.id
        )
        parsed_result = await session.execute(parsed_query)
        parsed = parsed_result.scalar_one_or_none()
        
        return {
            "application_id": application_id,
            "has_cover_letter": True,
            "filename": cover_letter_file.original_filename,
            "content": parsed.raw_text if parsed else None,
            "uploaded_at": cover_letter_file.created_at.isoformat() if cover_letter_file.created_at else None,
        }


async def read_linkedin_profile(candidate_id: int) -> Optional[Dict[str, Any]]:
    """Read LinkedIn profile data for a candidate.
    
    Returns imported LinkedIn profile data if available.
    
    Args:
        candidate_id: The candidate ID
        
    Returns:
        Dictionary containing LinkedIn data, or None if not imported
    """
    async with AsyncSessionLocal() as session:
        query = select(Candidate).where(Candidate.id == candidate_id)
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return None
        
        if not candidate.linkedin_url and not candidate.linkedin_data:
            return {
                "candidate_id": candidate_id,
                "has_linkedin": False,
                "profile_url": None,
            }
        
        linkedin_data = candidate.linkedin_data or {}
        
        return {
            "candidate_id": candidate_id,
            "has_linkedin": True,
            "profile_url": candidate.linkedin_url,
            # Profile data (if imported)
            "headline": linkedin_data.get("headline") or candidate.headline,
            "summary": linkedin_data.get("summary") or candidate.summary,
            "location": linkedin_data.get("location") or candidate.location,
            "connections": linkedin_data.get("connections"),
            "industry": linkedin_data.get("industry"),
            # Experience from LinkedIn
            "experience": linkedin_data.get("positions", []),
            # Education from LinkedIn
            "education": linkedin_data.get("education", []),
            # Skills and endorsements
            "skills": linkedin_data.get("skills", []),
            "endorsements": linkedin_data.get("endorsements", []),
            # Recommendations
            "recommendations_received": linkedin_data.get("recommendations", []),
            # Last updated
            "imported_at": candidate.linkedin_imported_at.isoformat() if hasattr(candidate, 'linkedin_imported_at') and candidate.linkedin_imported_at else None,
        }


async def read_portfolio(candidate_id: int) -> List[Dict[str, Any]]:
    """Read portfolio items for a candidate.
    
    Returns portfolio files and links associated with the candidate.
    
    Args:
        candidate_id: The candidate ID
        
    Returns:
        List of portfolio items
    """
    async with AsyncSessionLocal() as session:
        query = (
            select(Candidate)
            .options(
                selectinload(Candidate.applications).selectinload(Application.files),
            )
            .where(Candidate.id == candidate_id)
        )
        result = await session.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            return []
        
        portfolio_items = []
        
        # Add portfolio URL if present
        if candidate.portfolio_url:
            portfolio_items.append({
                "type": "url",
                "name": "Portfolio Website",
                "url": candidate.portfolio_url,
            })
        
        # Add GitHub if present
        if candidate.github_url:
            portfolio_items.append({
                "type": "url",
                "name": "GitHub Profile",
                "url": candidate.github_url,
            })
        
        # Collect portfolio files from all applications
        for app in (candidate.applications or []):
            for file in (app.files or []):
                if file.file_type == "portfolio":
                    # Get parsed content if available
                    parsed_query = select(ParsedResume).where(
                        ParsedResume.file_id == file.id
                    )
                    parsed_result = await session.execute(parsed_query)
                    parsed = parsed_result.scalar_one_or_none()
                    
                    portfolio_items.append({
                        "type": "file",
                        "name": file.original_filename,
                        "file_id": file.id,
                        "file_type": file.mime_type,
                        "size_bytes": file.size_bytes,
                        "content": parsed.raw_text if parsed else None,
                        "uploaded_at": file.created_at.isoformat() if file.created_at else None,
                        "application_id": app.id,
                    })
        
        return portfolio_items
