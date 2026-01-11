"""Resume parsing prompt templates."""

from agents.common.prompts import (
    PROFESSIONAL_TONE,
    JSON_OUTPUT,
    RESUME_PARSING_INSTRUCTIONS,
)


RESUME_PARSER_SYSTEM_PROMPT = f"""{PROFESSIONAL_TONE}

You are an expert resume parser and career document analyst. Your role is to extract 
structured information from resumes with high accuracy and attention to detail.

{RESUME_PARSING_INSTRUCTIONS}

{JSON_OUTPUT}

Ensure dates are in YYYY-MM-DD format (or YYYY-MM for month/year, or YYYY for year only).
If a field is not found in the resume, use null rather than making assumptions.
"""


RESUME_ENHANCEMENT_PROMPT = """Analyze this resume and provide suggestions for improvement:

1. Structure and Formatting
   - Is the layout clear and professional?
   - Are sections well-organized?
   - Is important information easy to find?

2. Content Quality
   - Are achievements quantified with metrics?
   - Are responsibilities clearly articulated?
   - Is the language professional and impactful?

3. Missing Elements
   - What key information is missing?
   - What sections could be added?
   - What details should be expanded?

4. Industry Best Practices
   - Does it follow current resume standards?
   - Is it ATS-friendly?
   - Is the length appropriate?

Provide specific, actionable recommendations."""


SKILL_EXTRACTION_PROMPT = """Extract and categorize skills from this resume:

Categories:
1. Technical Skills
   - Programming languages
   - Frameworks and libraries
   - Tools and platforms
   - Databases
   - Cloud technologies

2. Soft Skills
   - Leadership
   - Communication
   - Problem-solving
   - Teamwork
   - Time management

3. Domain Expertise
   - Industry-specific knowledge
   - Specialized methodologies
   - Business domains

4. Languages
   - Natural languages spoken
   - Proficiency levels

5. Certifications
   - Professional certifications
   - Licenses
   - Training programs

Return as structured JSON with skill names and proficiency levels where mentioned."""
