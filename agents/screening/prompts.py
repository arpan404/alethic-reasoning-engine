"""Screening agent prompt templates."""

from agents.common.prompts import (
    ANALYTICAL_TONE,
    EVALUATION_CRITERIA,
    SCORING_GUIDELINES,
    SCREENING_INSTRUCTIONS,
    JSON_OUTPUT,
)


SCREENING_SYSTEM_PROMPT = f"""{ANALYTICAL_TONE}

You are an expert recruiter and talent assessor. Your role is to fairly and 
objectively evaluate candidates against job requirements.

{EVALUATION_CRITERIA}

{SCORING_GUIDELINES}

{SCREENING_INSTRUCTIONS}

Be fair and unbiased. Focus on qualifications, not demographics.
Consider both hard skills and soft skills.
Look for transferable skills and growth potential.

{JSON_OUTPUT}
"""


QUALIFICATION_MATCH_PROMPT = """Analyze how well this candidate matches the job requirements:

Job Requirements:
{requirements}

Candidate Profile:
{candidate}

For each requirement:
1. State the requirement clearly
2. Indicate if the candidate meets it (Yes/No/Partial)
3. Provide evidence from their profile
4. Rate the match strength (Strong/Moderate/Weak/None)

Then provide:
- Overall qualification match percentage
- Key strengths relative to the role
- Significant gaps or concerns
- Transferable skills that could bridge gaps"""


FIT_ASSESSMENT_PROMPT = """Assess this candidate's fit for the role and company:

Technical Fit (40%):
- Do they have the required technical skills?
- What is their expertise level?
- Can they hit the ground running?

Experience Fit (30%):
- Do they have relevant industry experience?
- Have they worked in similar roles?
- What's their seniority level match?

Cultural Fit (20%):
- Do their values align with company culture?
- Does their work style match the team?
- Will they thrive in this environment?

Growth Potential (10%):
- What is their learning trajectory?
- Are they open to new challenges?
- Do they show adaptability?

Provide a score for each category and an overall fit score."""


RED_FLAGS_PROMPT = """Identify any potential concerns or red flags in this candidate profile:

Look for:
1. Employment gaps (explain or concern?)
2. Frequent job changes (career growth or instability?)
3. Skills mismatch (can it be overcome?)
4. Experience level (over/under-qualified?)
5. Location concerns (relocation/remote work?)
6. Compensation expectations (alignment?)
7. Timeline/availability issues

For each item:
- Describe the concern
- Rate severity (Low/Medium/High)
- Suggest mitigation strategies
- Recommend follow-up questions

Be balanced - some "red flags" may have reasonable explanations."""


INTERVIEW_RECOMMENDATION_PROMPT = """Based on the screening assessment, provide interview recommendations:

Should we proceed? (Yes/No/Maybe - provide clear reasoning)

If Yes or Maybe:
1. Recommended interview stage (phone screen/technical/onsite)
2. Key areas to explore in interview:
   - Technical skills to validate
   - Experience claims to verify
   - Soft skills to assess
   - Concerns to address
3. Specific questions to ask
4. Red flags to probe
5. Estimated time to hire if successful

If No:
1. Primary reasons for rejection
2. Feedback for candidate (constructive)
3. Could they be considered for other roles?"""
