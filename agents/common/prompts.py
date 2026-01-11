"""Shared prompt templates for agents."""

# System prompts
PROFESSIONAL_TONE = """You are a professional, courteous, and helpful assistant. 
Always maintain a professional tone and provide accurate, well-structured responses."""

ANALYTICAL_TONE = """You are an analytical expert who provides detailed, data-driven insights.
Focus on objectivity, fairness, and evidence-based reasoning."""

# Common instructions
STRUCTURED_OUTPUT = """Provide your response in a clear, structured format with:
1. Clear headings and sections
2. Bullet points for lists
3. Numbered steps for procedures
4. Specific examples where helpful"""

JSON_OUTPUT = """Your response must be valid JSON that can be parsed directly.
Do not include any markdown formatting or code blocks.
Ensure all strings are properly escaped."""

# Evaluation criteria
EVALUATION_CRITERIA = """When evaluating, consider:
1. Relevance - How well does this match the requirements?
2. Quality - What is the level of expertise demonstrated?
3. Experience - What is the depth and breadth of experience?
4. Cultural fit - How well does this align with values and work style?
5. Growth potential - What is the capacity for learning and development?"""

# Scoring guidelines
SCORING_GUIDELINES = """Scoring scale (0-100):
- 90-100: Exceptional match, highly recommended
- 80-89: Strong match, recommended
- 70-79: Good match, consider carefully
- 60-69: Moderate match, has potential but gaps exist
- 50-59: Weak match, significant gaps
- Below 50: Poor match, not recommended

Provide specific reasoning for your score."""

# Resume parsing instructions
RESUME_PARSING_INSTRUCTIONS = """Extract all relevant information from the resume:

Contact Information:
- Full name
- Email address
- Phone number
- Location (city, state/country)
- LinkedIn URL
- GitHub URL
- Portfolio/website URL

Professional Summary:
- Brief overview of candidate's profile
- Key strengths and expertise

Work Experience:
For each position:
- Company name
- Job title
- Start date (YYYY-MM-DD format)
- End date (YYYY-MM-DD format or "Present")
- Location
- Key responsibilities (bullet points)
- Notable achievements (bullet points)
- Technologies/tools used

Education:
For each degree:
- Institution name
- Degree type (Bachelor's, Master's, PhD, etc.)
- Field of study
- Start date
- End date (or expected)
- GPA (if mentioned)
- Relevant coursework
- Honors/awards

Skills:
- Technical skills
- Soft skills
- Languages (programming and spoken)
- Certifications
- Tools and technologies

Additional:
- Projects (personal or professional)
- Publications
- Patents
- Volunteer work
- Awards and recognition"""

# Screening instructions
SCREENING_INSTRUCTIONS = """Screen this candidate against the job requirements:

Step 1: Requirements Analysis
- List all required qualifications
- List all preferred qualifications
- Identify must-have skills vs. nice-to-have

Step 2: Candidate Evaluation
- Match candidate's experience to requirements
- Identify strengths and strong matches
- Identify gaps or areas of concern
- Consider transferable skills

Step 3: Scoring
- Calculate overall fit score (0-100)
- Provide category scores:
  * Technical skills match
  * Experience level match
  * Cultural fit potential
  * Growth potential

Step 4: Recommendation
- Clear recommendation: Proceed, Review, or Reject
- Key supporting points
- Suggested interview focus areas if proceeding
- Any red flags or concerns"""

# Interview question generation
INTERVIEW_QUESTIONS_PROMPT = """Generate insightful interview questions based on:
1. Job requirements
2. Candidate's background
3. Specific areas to probe

Question types:
- Technical questions (assess skills)
- Behavioral questions (assess soft skills)
- Situational questions (assess problem-solving)
- Experience-based questions (verify claims)

For each question, provide:
- The question itself
- Why you're asking it (what it reveals)
- What to look for in the answer
- Possible follow-up questions"""

# Email generation
EMAIL_GENERATION_PROMPT = """Compose a professional email that:
1. Has a clear, relevant subject line
2. Opens with appropriate greeting
3. States purpose clearly in first paragraph
4. Provides necessary details
5. Includes clear call-to-action
6. Closes professionally
7. Uses appropriate tone for the context

Keep it concise but complete."""
