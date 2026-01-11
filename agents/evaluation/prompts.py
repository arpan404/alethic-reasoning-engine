"""Evaluation agent prompt templates."""

from agents.common.prompts import (
    ANALYTICAL_TONE,
    EVALUATION_CRITERIA,
    SCORING_GUIDELINES,
    JSON_OUTPUT,
)


EVALUATION_SYSTEM_PROMPT = f"""{ANALYTICAL_TONE}

You are a senior talent assessment expert with deep experience in evaluating 
candidates across multiple dimensions. Your evaluations are thorough, fair, 
and predictive of job success.

{EVALUATION_CRITERIA}

Additional Evaluation Dimensions:

Technical Competency (35%):
- Depth and breadth of technical skills
- Hands-on experience with relevant technologies
- Problem-solving ability
- Learning agility

Professional Experience (30%):
- Relevant industry experience
- Career progression and growth
- Complexity of projects handled
- Leadership and impact

Cultural Alignment (20%):
- Values alignment with company culture
- Work style compatibility
- Team collaboration potential
- Communication effectiveness

Growth Potential (15%):
- Learning mindset and curiosity
- Adaptability to change
- Career ambitions alignment
- Long-term fit potential

{SCORING_GUIDELINES}

Also provide:
- Predicted 1-year performance rating
- Retention risk assessment
- Onboarding timeline and focus areas
- 90-day success metrics

{JSON_OUTPUT}
"""


COMPREHENSIVE_EVALUATION_PROMPT = """Conduct a thorough evaluation of this candidate for the role:

CANDIDATE INFORMATION:
Name: {name}
Current Role: {current_role}
Experience: {years_experience} years
Education: {education}

TECHNICAL ASSESSMENT:
Skills: {skills}
Projects: {projects}
Achievements: {achievements}

INTERVIEW PERFORMANCE:
{interview_notes}

JOB REQUIREMENTS:
{requirements}

COMPANY CULTURE:
{culture}

Provide comprehensive analysis including:

1. OVERALL FIT SCORE (0-100)
2. CATEGORY SCORES:
   - Technical Skills: X/100
   - Professional Experience: X/100
   - Cultural Fit: X/100
   - Growth Potential: X/100

3. KEY STRENGTHS (Top 5):
   - [Strength with specific evidence]

4. AREAS FOR DEVELOPMENT (If any):
   - [Area with constructive feedback]

5. PREDICTED JOB PERFORMANCE:
   - First 30 days:
   - First 90 days:
   - First year:

6. RETENTION LIKELIHOOD:
   - Score: X/100
   - Factors: [List key factors]

7. COMPENSATION RECOMMENDATION:
   - Range: $X - $Y
   - Rationale: [Justification]

8. HIRING RECOMMENDATION:
   - Decision: [Strong Yes/Yes/Maybe/No/Strong No]
   - Confidence: [High/Medium/Low]
   - Reasoning: [Clear justification]

9. ONBOARDING FOCUS:
   - Priority areas for training
   - Mentorship needs
   - Integration timeline

10. SUCCESS METRICS (90 days):
    - [Specific, measurable goals]
"""


COMPARATIVE_EVALUATION_PROMPT = """Compare these candidates for the role and rank them:

CANDIDATES:
{candidates}

JOB REQUIREMENTS:
{requirements}

For each candidate provide:
1. Overall fit score
2. Key differentiators
3. Unique strengths
4. Concerns or gaps

Then provide:
- Ranked recommendation (1st, 2nd, 3rd choice)
- Rationale for ranking
- Trade-offs between candidates
- Final hiring recommendation

Consider:
- Who can start soonest and make immediate impact?
- Who has highest long-term potential?
- Who best fits team dynamics?
- Who offers best value for compensation?
"""


RISK_ASSESSMENT_PROMPT = """Assess hiring risks for this candidate:

CANDIDATE PROFILE:
{candidate}

Evaluate risk in these areas:

1. TECHNICAL RISK:
   - Can they perform the job technically?
   - Gaps in required skills?
   - Learning curve concerns?

2. CULTURAL RISK:
   - Will they fit with the team?
   - Value alignment concerns?
   - Communication style compatibility?

3. RETENTION RISK:
   - Likelihood to stay long-term?
   - Career goals alignment?
   - Compensation expectations reasonable?

4. PERFORMANCE RISK:
   - Past performance indicators?
   - Red flags in work history?
   - References or concerns?

5. MARKET RISK:
   - How competitive is offer needed?
   - Likelihood of counteroffers?
   - Other opportunities they're considering?

For each risk:
- Rate: Low/Medium/High
- Describe the risk
- Suggest mitigation strategies
- Impact on hiring decision

Overall Risk Profile: Low/Medium/High
Proceed with Hire: Yes/No/Conditional
"""
