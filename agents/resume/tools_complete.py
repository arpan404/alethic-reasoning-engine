"""Resume parsing and analysis tools."""

import re
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from agents.common.tools import (
    extract_email,
    extract_phone,
    extract_linkedin_url,
    extract_github_url,
    extract_urls,
    parse_date,
    calculate_duration,
)

logger = logging.getLogger(__name__)


def extract_contact_info(resume_text: str) -> Dict[str, Optional[str]]:
    """Extract contact information from resume.
    
    Args:
        resume_text: Resume text content
        
    Returns:
        Dictionary containing contact info
    """
    try:
        # Extract name (usually first few lines)
        lines = [line.strip() for line in resume_text.split('\n') if line.strip()]
        # Look for name pattern (capitalized words at start)
        name_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$'
        name = None
        for line in lines[:5]:  # Check first 5 lines
            if re.match(name_pattern, line):
                name = line
                break
        
        # Extract contact details
        email = extract_email(resume_text)
        phone = extract_phone(resume_text)
        linkedin = extract_linkedin_url(resume_text)
        github = extract_github_url(resume_text)
        
        # Extract location
        location_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\b'
        location_match = re.search(location_pattern, resume_text)
        location = location_match.group(0) if location_match else None
        
        return {
            "name": name or (lines[0] if lines else None),
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "location": location,
        }
    
    except Exception as e:
        logger.error(f"Error extracting contact info: {e}")
        return {}


def extract_experience(resume_text: str) -> List[Dict[str, Any]]:
    """Extract work experience from resume.
    
    Args:
        resume_text: Resume text content
        
    Returns:
        List of experience entries
    """
    try:
        # Find experience section
        exp_section_pattern = r'(?:WORK EXPERIENCE|PROFESSIONAL EXPERIENCE|EXPERIENCE|EMPLOYMENT HISTORY)(.*?)(?=\n[A-Z\s]{3,}:|$)'
        match = re.search(exp_section_pattern, resume_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            logger.warning("Could not find experience section")
            return []
        
        experience_text = match.group(1)
        experiences = []
        
        # Pattern: Job Title | Company | Dates
        job_pattern = r'([A-Z][A-Za-z\s,]+)\s*[|–-]\s*([A-Z][A-Za-z\s&,\.]+)\s*\n?\s*([A-Z][a-z]+\s+\d{4}\s*[-–]\s*(?:[A-Z][a-z]+\s+\d{4}|Present|Current))'
        
        for match in re.finditer(job_pattern, experience_text):
            title = match.group(1).strip()
            company = match.group(2).strip()
            dates = match.group(3).strip()
            
            # Parse dates
            date_parts = re.search(r'([A-Z][a-z]+\s+\d{4})\s*[-–]\s*([A-Z][a-z]+\s+\d{4}|Present|Current)', dates)
            
            start_date = None
            end_date = None
            duration = None
            
            if date_parts:
                start_str = date_parts.group(1)
                end_str = date_parts.group(2)
                
                start_date = parse_date(start_str)
                if end_str.lower() not in ['present', 'current']:
                    end_date = parse_date(end_str)
                
                if start_date:
                    duration = calculate_duration(start_date, end_date)
            
            experiences.append({
                "title": title,
                "company": company,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "current": end_str.lower() in ['present', 'current'] if date_parts else False,
                "duration": duration,
            })
        
        return experiences
    
    except Exception as e:
        logger.error(f"Error extracting experience: {e}")
        return []


def extract_education(resume_text: str) -> List[Dict[str, Any]]:
    """Extract education from resume.
    
    Args:
        resume_text: Resume text content
        
    Returns:
        List of education entries
    """
    try:
        # Find education section
        edu_pattern = r'(?:EDUCATION|ACADEMIC BACKGROUND)(.*?)(?=\n[A-Z\s]{3,}:|$)'
        match = re.search(edu_pattern, resume_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            logger.warning("Could not find education section")
            return []
        
        education_text = match.group(1)
        educations = []
        
        # Extract degrees
        degree_patterns = [
            r'(PhD|Ph\.D\.|Doctor of Philosophy)',
            r'(Master|M\.S\.|M\.A\.|MBA|M\.B\.A\.)',
            r'(Bachelor|B\.S\.|B\.A\.|B\.Sc\.|B\.Tech)',
            r'(Associate|A\.S\.|A\.A\.)',
        ]
        
        degrees = []
        for pattern in degree_patterns:
            degrees.extend(re.findall(pattern, education_text, re.IGNORECASE))
        
        # Extract schools
        school_pattern = r'(University|College|Institute|School) of [A-Z][A-Za-z\s]+|[A-Z][A-Za-z\s]+ (University|College|Institute)'
        schools = re.findall(school_pattern, education_text)
        schools = [' '.join(s) if isinstance(s, tuple) else s for s in schools]
        
        # Extract years
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        years = re.findall(year_pattern, education_text)
        
        # Extract GPA
        gpa_pattern = r'GPA:?\s*(\d\.\d+)'
        gpa_match = re.search(gpa_pattern, education_text, re.IGNORECASE)
        gpa = float(gpa_match.group(1)) if gpa_match else None
        
        # Combine information
        max_entries = max(len(degrees), len(schools), len(years))
        for i in range(max_entries):
            educations.append({
                "degree": degrees[i] if i < len(degrees) else None,
                "school": schools[i].strip() if i < len(schools) else None,
                "graduation_year": int(years[i]) if i < len(years) else None,
                "gpa": gpa if i == 0 else None,
            })
        
        return educations
    
    except Exception as e:
        logger.error(f"Error extracting education: {e}")
        return []


def extract_skills(resume_text: str, skill_taxonomy: Optional[List[str]] = None) -> List[str]:
    """Extract skills from resume.
    
    Args:
        resume_text: Resume text content
        skill_taxonomy: Optional list of known skills to match against
        
    Returns:
        List of skills found
    """
    try:
        # Find skills section
        skills_pattern = r'(?:SKILLS|TECHNICAL SKILLS|CORE COMPETENCIES)(.*?)(?=\n[A-Z\s]{3,}:|$)'
        match = re.search(skills_pattern, resume_text, re.IGNORECASE | re.DOTALL)
        
        skills_text = match.group(1) if match else resume_text
        skills = []
        
        # If taxonomy provided, match against it
        if skill_taxonomy:
            text_lower = skills_text.lower()
            for skill in skill_taxonomy:
                if skill.lower() in text_lower:
                    skills.append(skill)
        
        # Extract from comma-separated lists
        list_matches = re.findall(r'[\w\s+#\.]+(?:,[\w\s+#\.]+)+', skills_text)
        for match in list_matches:
            items = [item.strip() for item in match.split(',')]
            skills.extend(items)
        
        # Extract bullet points
        bullet_matches = re.findall(r'[•\-\*]\s*([\w\s+#\.]+)', skills_text)
        skills.extend([s.strip() for s in bullet_matches])
        
        # Remove duplicates
        return list(set(skill.strip() for skill in skills if skill.strip()))
    
    except Exception as e:
        logger.error(f"Error extracting skills: {e}")
        return []


def extract_certifications(resume_text: str) -> List[Dict[str, Any]]:
    """Extract certifications from resume.
    
    Args:
        resume_text: Resume text content
        
    Returns:
        List of certifications
    """
    try:
        # Find certifications section
        cert_pattern = r'(?:CERTIFICATIONS|CERTIFICATES|LICENSES)(.*?)(?=\n[A-Z\s]{3,}:|$)'
        match = re.search(cert_pattern, resume_text, re.IGNORECASE | re.DOTALL)
        
        if not match:
            return []
        
        cert_text = match.group(1)
        certifications = []
        
        # Look for certification patterns
        cert_name_pattern = r'([A-Z][A-Za-z\s]+(?:Certified|Certification|Certificate))'
        cert_names = re.findall(cert_name_pattern, cert_text)
        
        # Look for years
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        years = re.findall(year_pattern, cert_text)
        
        for i, cert_name in enumerate(cert_names):
            certifications.append({
                "name": cert_name.strip(),
                "year": int(years[i]) if i < len(years) else None,
            })
        
        return certifications
    
    except Exception as e:
        logger.error(f"Error extracting certifications: {e}")
        return []


def calculate_total_experience(experiences: List[Dict[str, Any]]) -> float:
    """Calculate total years of experience.
    
    Args:
        experiences: List of experience entries
        
    Returns:
        Total years of experience
    """
    total_months = 0
    
    for exp in experiences:
        if exp.get("duration"):
            total_months += exp["duration"].get("total_months", 0)
    
    return round(total_months / 12, 1)


def parse_resume(resume_text: str, skill_taxonomy: Optional[List[str]] = None) -> Dict[str, Any]:
    """Parse complete resume into structured data.
    
    Args:
        resume_text: Resume text content
        skill_taxonomy: Optional list of known skills
        
    Returns:
        Structured resume data
    """
    try:
        contact_info = extract_contact_info(resume_text)
        experience = extract_experience(resume_text)
        education = extract_education(resume_text)
        skills = extract_skills(resume_text, skill_taxonomy)
        certifications = extract_certifications(resume_text)
        
        return {
            "contact_info": contact_info,
            "experience": experience,
            "education": education,
            "skills": skills,
            "certifications": certifications,
            "total_experience_years": calculate_total_experience(experience),
            "parsed_at": datetime.now().isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        return {}
