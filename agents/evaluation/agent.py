"""Evaluation agent for comprehensive candidate assessment."""

from typing import Dict, Any
from agents.base import BaseAgent
from agents.registry import register_agent
from agents.evaluation.tools import (
    calculate_technical_score,
    assess_cultural_fit,
    predict_success_likelihood,
)
from agents.evaluation.prompts import EVALUATION_SYSTEM_PROMPT


@register_agent("evaluation")
class EvaluationAgent(BaseAgent):
    """Agent for in-depth candidate evaluation and assessment."""

    def __init__(self):
        super().__init__(
            name="evaluation",
            instructions=EVALUATION_SYSTEM_PROMPT,
            tools=[
                calculate_technical_score,
                assess_cultural_fit,
                predict_success_likelihood,
            ],
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate candidate comprehensively.
        
        Args:
            input_data: Dictionary with 'candidate_profile', 'job_requirements',
                       'company_culture', and optional 'interview_notes'
            
        Returns:
            Comprehensive evaluation results with scores and recommendations
        """
        candidate = input_data.get("candidate_profile", {})
        job_requirements = input_data.get("job_requirements", {})
        company_culture = input_data.get("company_culture", {})
        interview_notes = input_data.get("interview_notes", "")
        
        prompt = f"""Conduct a comprehensive evaluation of this candidate:

CANDIDATE PROFILE:
{candidate}

JOB REQUIREMENTS:
{job_requirements}

COMPANY CULTURE:
{company_culture}

INTERVIEW NOTES:
{interview_notes}

Provide a detailed evaluation including:
1. Overall fit score (0-100)
2. Category scores (technical, experience, cultural, growth potential)
3. Key strengths (top 5)
4. Areas of concern (if any)
5. Predicted job performance
6. Retention likelihood
7. Hiring recommendation (Strong Yes/Yes/Maybe/No/Strong No)
8. Compensation recommendation
9. Onboarding focus areas
10. 90-day success metrics

Format as structured JSON."""

        response = await self.run(prompt)
        
        return {
            "status": "success",
            "evaluation": response,
            "timestamp": input_data.get("timestamp"),
        }
