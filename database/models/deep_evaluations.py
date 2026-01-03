"""
Deep Application Evaluation System

Comprehensive evaluation framework for in-depth candidate assessment including:
- Portfolio analysis and project evaluation
- Multi-dimensional scoring with JSON storage
- Work sample evaluation
- Cultural fit assessment
- Technical depth analysis
- Structured evaluation data with flexible schemas
"""

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, BigInteger, DateTime, func, Text, Boolean, ForeignKey, Integer, Numeric, JSON, Enum as SQLEnum
from database.engine import Base
from database.security import ComplianceMixin, compliance_column, DataSensitivity, GDPRDataCategory, DataRetentionPeriod
from datetime import datetime
from enum import Enum as PyEnum


class EvaluationDimension(str, PyEnum):
    """Evaluation dimensions for comprehensive assessment."""
    TECHNICAL_SKILLS = "technical_skills"
    SOFT_SKILLS = "soft_skills"
    CULTURAL_FIT = "cultural_fit"
    PORTFOLIO_QUALITY = "portfolio_quality"
    WORK_EXPERIENCE = "work_experience"
    EDUCATION = "education"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    LEADERSHIP = "leadership"
    CREATIVITY = "creativity"


class PortfolioItemType(str, PyEnum):
    """Types of portfolio items."""
    PROJECT = "project"
    PUBLICATION = "publication"
    PRESENTATION = "presentation"
    OPEN_SOURCE = "open_source"
    DESIGN = "design"
    WRITING = "writing"
    VIDEO = "video"
    CERTIFICATION = "certification"
    AWARD = "award"
    OTHER = "other"


class ApplicationDeepEvaluation(Base, ComplianceMixin):
    """
    Comprehensive deep evaluation of applications with structured JSON data.
    Stores multi-dimensional assessment with flexible schema.
    """
    __tablename__ = "application_deep_evaluations"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )
    
    # Overall evaluation
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # 0-100
    overall_rating: Mapped[str] = mapped_column(String(50), nullable=False)  # excellent, good, average, poor
    
    # Dimensional scores (JSON for flexibility)
    dimensional_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "technical_skills": {"score": 85, "weight": 0.3, "evidence": [...]},
    #   "soft_skills": {"score": 90, "weight": 0.2, "evidence": [...]},
    #   "cultural_fit": {"score": 88, "weight": 0.2, "evidence": [...]},
    #   "portfolio_quality": {"score": 92, "weight": 0.3, "evidence": [...]}
    # }
    
    # Detailed evaluation data (flexible JSON schema)
    evaluation_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "strengths": ["Strong technical background", "Excellent portfolio"],
    #   "weaknesses": ["Limited leadership experience"],
    #   "opportunities": ["Great fit for senior role"],
    #   "risks": ["May require relocation support"],
    #   "key_achievements": [...],
    #   "red_flags": [...],
    #   "cultural_alignment": {...},
    #   "growth_potential": {...}
    # }
    
    # Portfolio analysis summary
    portfolio_analysis: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "total_projects": 12,
    #   "quality_score": 88,
    #   "diversity_score": 85,
    #   "relevance_score": 92,
    #   "top_projects": [...],
    #   "technologies_used": [...],
    #   "impact_metrics": {...}
    # }
    
    # Work sample evaluation
    work_sample_evaluation: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "code_quality": 90,
    #   "design_quality": 85,
    #   "documentation": 88,
    #   "best_practices": 92,
    #   "creativity": 87,
    #   "detailed_feedback": {...}
    # }
    
    # Recommendation
    recommendation: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # strong_hire, hire, maybe, no_hire
    recommendation_reasoning: Mapped[str | None] = mapped_column(Text)
    
    # Evaluator info
    evaluated_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    evaluation_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # manual, ai_assisted, fully_automated
    
    # AI assistance
    ai_insights: Mapped[dict | None] = mapped_column(JSON)
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    
    # Timestamps
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PortfolioItem(Base, ComplianceMixin):
    """
    Individual portfolio items (projects, publications, etc.) with detailed evaluation.
    """
    __tablename__ = "portfolio_items"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    
    # Item details
    item_type: Mapped[PortfolioItemType] = mapped_column(
        SQLEnum(PortfolioItemType, name="portfolio_item_type"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # URLs and files
    url: Mapped[str | None] = mapped_column(String(1000))
    repository_url: Mapped[str | None] = mapped_column(String(1000))
    demo_url: Mapped[str | None] = mapped_column(String(1000))
    file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id"))
    
    # Project metadata (flexible JSON)
    metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "technologies": ["Python", "React", "PostgreSQL"],
    #   "role": "Lead Developer",
    #   "team_size": 5,
    #   "duration_months": 6,
    #   "impact": "Increased efficiency by 40%",
    #   "metrics": {"users": 10000, "revenue": 50000},
    #   "challenges": [...],
    #   "solutions": [...]
    # }
    
    # Evaluation scores
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 0-100
    relevance_score: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 0-100
    complexity_score: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 0-100
    impact_score: Mapped[float | None] = mapped_column(Numeric(5, 2))  # 0-100
    
    # Detailed evaluation (JSON)
    evaluation_details: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "technical_assessment": {...},
    #   "design_assessment": {...},
    #   "code_quality": {...},
    #   "documentation_quality": {...},
    #   "innovation_level": {...},
    #   "business_value": {...}
    # }
    
    # AI analysis
    ai_analysis: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "technologies_detected": [...],
    #   "code_quality_metrics": {...},
    #   "design_patterns_used": [...],
    #   "best_practices_score": 85,
    #   "security_assessment": {...},
    #   "performance_indicators": {...}
    # }
    
    # Featured/highlighted
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int | None] = mapped_column(Integer)
    
    # Timestamps
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class WorkSampleSubmission(Base, ComplianceMixin):
    """
    Work samples submitted by candidates for evaluation.
    """
    __tablename__ = "work_sample_submissions"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )
    
    # Sample details
    sample_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # code, design, writing, presentation, video
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Submission
    file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("files.id"))
    url: Mapped[str | None] = mapped_column(String(1000))
    repository_url: Mapped[str | None] = mapped_column(String(1000))
    
    # Evaluation criteria (JSON)
    evaluation_criteria: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "code_quality": {"weight": 0.3, "description": "..."},
    #   "functionality": {"weight": 0.3, "description": "..."},
    #   "design": {"weight": 0.2, "description": "..."},
    #   "documentation": {"weight": 0.2, "description": "..."}
    # }
    
    # Evaluation results (JSON)
    evaluation_results: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "code_quality": {"score": 85, "feedback": "...", "evidence": [...]},
    #   "functionality": {"score": 90, "feedback": "...", "evidence": [...]},
    #   "design": {"score": 88, "feedback": "...", "evidence": [...]},
    #   "documentation": {"score": 82, "feedback": "...", "evidence": [...]}
    # }
    
    # Overall scores
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    
    # AI analysis
    ai_analysis: Mapped[dict | None] = mapped_column(JSON)
    # Example for code:
    # {
    #   "complexity_metrics": {...},
    #   "code_smells": [...],
    #   "security_issues": [...],
    #   "performance_analysis": {...},
    #   "test_coverage": 85,
    #   "documentation_coverage": 78
    # }
    
    # Evaluator
    evaluated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    
    # Timestamps
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CulturalFitAssessment(Base, ComplianceMixin):
    """
    Cultural fit assessment with structured evaluation data.
    """
    __tablename__ = "cultural_fit_assessments"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )
    
    # Organization values alignment
    values_alignment: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "innovation": {"score": 90, "evidence": [...], "examples": [...]},
    #   "collaboration": {"score": 85, "evidence": [...], "examples": [...]},
    #   "integrity": {"score": 95, "evidence": [...], "examples": [...]},
    #   "customer_focus": {"score": 88, "evidence": [...], "examples": [...]}
    # }
    
    # Work style assessment
    work_style: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "communication_style": "direct",
    #   "decision_making": "data_driven",
    #   "conflict_resolution": "collaborative",
    #   "work_pace": "fast",
    #   "autonomy_preference": "high",
    #   "feedback_style": "constructive"
    # }
    
    # Team dynamics
    team_fit: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "collaboration_score": 88,
    #   "leadership_potential": 85,
    #   "mentorship_capability": 90,
    #   "team_player_score": 92,
    #   "diversity_contribution": {...}
    # }
    
    # Behavioral indicators
    behavioral_indicators: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "growth_mindset": {"score": 90, "indicators": [...]},
    #   "adaptability": {"score": 85, "indicators": [...]},
    #   "resilience": {"score": 88, "indicators": [...]},
    #   "empathy": {"score": 92, "indicators": [...]}
    # }
    
    # Overall fit
    overall_fit_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    fit_recommendation: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # excellent_fit, good_fit, moderate_fit, poor_fit
    
    # Assessment method
    assessment_method: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # interview, questionnaire, ai_analysis, behavioral_assessment
    
    # Assessor
    assessed_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    
    # Timestamps
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TechnicalDepthAssessment(Base, ComplianceMixin):
    """
    Deep technical assessment with detailed skill evaluation.
    """
    __tablename__ = "technical_depth_assessments"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    application_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), nullable=False, index=True
    )
    
    # Skill depth analysis (JSON)
    skill_depth: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "Python": {
    #     "proficiency_level": "expert",
    #     "years_experience": 8,
    #     "depth_score": 92,
    #     "breadth_score": 88,
    #     "frameworks": ["Django", "FastAPI", "Flask"],
    #     "advanced_concepts": ["async", "metaclasses", "decorators"],
    #     "projects_count": 15,
    #     "evidence": [...]
    #   },
    #   "JavaScript": {...}
    # }
    
    # Domain expertise
    domain_expertise: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "machine_learning": {
    #     "expertise_level": "advanced",
    #     "score": 88,
    #     "specializations": ["NLP", "Computer Vision"],
    #     "tools": ["TensorFlow", "PyTorch"],
    #     "publications": [...],
    #     "projects": [...]
    #   }
    # }
    
    # Problem-solving assessment
    problem_solving: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "analytical_thinking": 90,
    #   "algorithmic_complexity": 85,
    #   "system_design": 88,
    #   "debugging_skills": 92,
    #   "optimization_ability": 87,
    #   "examples": [...]
    # }
    
    # Architecture and design
    architecture_skills: Mapped[dict | None] = mapped_column(JSON)
    # Example:
    # {
    #   "system_design_score": 88,
    #   "scalability_understanding": 90,
    #   "security_awareness": 85,
    #   "design_patterns": [...],
    #   "architectural_decisions": [...]
    # }
    
    # Overall technical score
    overall_technical_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    technical_level: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # junior, mid, senior, staff, principal
    
    # Assessor
    assessed_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    
    # Timestamps
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EvaluationTemplate(Base):
    """
    Reusable evaluation templates with custom criteria and JSON schemas.
    """
    __tablename__ = "evaluation_templates"
    
    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )
    
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id"), nullable=False, index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )
    
    # Template details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    template_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # deep_evaluation, portfolio, work_sample, cultural_fit, technical
    
    # Evaluation schema (flexible JSON)
    evaluation_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example:
    # {
    #   "dimensions": [
    #     {
    #       "name": "technical_skills",
    #       "weight": 0.4,
    #       "criteria": [
    #         {"name": "coding_ability", "weight": 0.5, "scale": "0-100"},
    #         {"name": "system_design", "weight": 0.5, "scale": "0-100"}
    #       ]
    #     },
    #     {
    #       "name": "soft_skills",
    #       "weight": 0.3,
    #       "criteria": [...]
    #     }
    #   ],
    #   "required_fields": [...],
    #   "optional_fields": [...],
    #   "scoring_method": "weighted_average"
    # }
    
    # Default values
    default_values: Mapped[dict | None] = mapped_column(JSON)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
