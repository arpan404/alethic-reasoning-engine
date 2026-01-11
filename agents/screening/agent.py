"""Screening agent for evaluating applications."""

from typing import Dict, Any
from agents.base import BaseAgent
from agents.registry import register_agent
from agents.screening.tools import calculate_fit_score, check_requirements


@register_agent("screening")
class ScreeningAgent(BaseAgent):
    """Agent for screening and evaluating job applications."""

    def __init__(self):
        super().__init__(
            name="screening",
            instructions="""You are an expert recruiter evaluating job applications.

Your task is to:
1. Review the candidate's resume and application
2. Compare qualifications against job requirements
3. Evaluate relevant experience and skills
4. Assess cultural fit based on values and work style
5. Provide a fit score (0-100) with detailed reasoning

Be objective and fair. Consider:
- Required vs preferred qualifications
- Transferable skills
- Growth potential
- Red flags or concerns

Provide constructive feedback for both acceptance and rejection decisions.""",
            tools=[
                calculate_fit_score,
                check_requirements,
            ],
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Screen application and provide evaluation.
        
        Args:
            input_data: Dictionary with 'candidate_data' and 'job_requirements'
            
        Returns:
            Screening results with score and recommendations
        """
        candidate_data = input_data.get("candidate_data", {})
        job_requirements = input_data.get("job_requirements", {})
        
        prompt = f"""Evaluate this candidate for the position:

Job Requirements:
{job_requirements}

Candidate Profile:
{candidate_data}

Provide a detailed evaluation including:
1. Fit score (0-100)
2. Strengths and matches
3. Gaps or concerns
4. Recommendation (proceed, reject, needs review)
5. Key questions for interview (if proceeding)"""

        response = await self.run(prompt)
        
        return {
            "status": "success",
            "evaluation": response,
        }
