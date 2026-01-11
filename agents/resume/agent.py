"""Resume parsing and analysis agent."""

from typing import Dict, Any
from agents.base import BaseAgent
from agents.registry import register_agent
from agents.resume.tools import extract_contact_info, extract_experience, extract_education


@register_agent("resume")
class ResumeAgent(BaseAgent):
    """Agent for parsing and analyzing resumes."""

    def __init__(self):
        super().__init__(
            name="resume",
            instructions="""You are a resume parsing expert. Your job is to extract structured information from resumes.
            
Extract the following information:
- Contact information (name, email, phone, location, linkedin, github)
- Work experience (company, title, dates, description, achievements)
- Education (institution, degree, field, dates, GPA)
- Skills (technical skills, soft skills, languages, certifications)
- Summary/objective
- Projects
- Publications
- Awards

Format dates consistently as YYYY-MM-DD.
Extract all relevant details accurately.""",
            tools=[
                extract_contact_info,
                extract_experience,
                extract_education,
            ],
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse resume and extract structured data.
        
        Args:
            input_data: Dictionary with 'resume_text' key
            
        Returns:
            Structured resume data
        """
        resume_text = input_data.get("resume_text", "")
        
        prompt = f"""Parse the following resume and extract all relevant information in a structured format:

{resume_text}

Provide the output as a structured JSON object."""

        response = await self.run(prompt)
        
        # Parse response into structured format
        # TODO: Implement proper JSON parsing and validation
        
        return {
            "status": "success",
            "parsed_data": response,
        }
