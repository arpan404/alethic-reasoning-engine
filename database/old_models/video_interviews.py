from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    String,
    BigInteger,
    DateTime,
    func,
    Text,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    JSON,
)
from database.engine import Base
from datetime import datetime


class VideoInterview(Base):
    """Video interview sessions with AI analysis support."""

    __tablename__ = "video_interviews"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    # Relationships
    interview_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("interviews.id"), index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("candidates.id"), nullable=False, index=True
    )
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("applicants.id"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("jobs.id"), index=True
    )

    # Interview details
    interview_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # live, asynchronous, ai_screening
    status: Mapped[str] = mapped_column(
        String(50), default="scheduled", nullable=False, index=True
    )  # scheduled, in_progress, completed, cancelled

    # Meeting info (for live interviews)
    meeting_url: Mapped[str | None] = mapped_column(String(500))
    meeting_platform: Mapped[str | None] = mapped_column(
        String(50)
    )  # zoom, teams, google_meet

    # Timestamps
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)

    # AI analysis flags
    enable_transcription: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    enable_sentiment_analysis: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    enable_keyword_extraction: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

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
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )


class VideoRecording(Base):
    """Video file references and metadata."""

    __tablename__ = "video_recordings"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    video_interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("video_interviews.id"), nullable=False, index=True
    )
    file_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("files.id"), nullable=False, index=True
    )

    # Recording details
    recording_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # full_recording, highlight, clip
    segment_start_time: Mapped[int | None] = mapped_column(Integer)  # seconds
    segment_end_time: Mapped[int | None] = mapped_column(Integer)  # seconds

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, processing, completed, failed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VideoTranscript(Base):
    """AI-generated transcripts from video interviews."""

    __tablename__ = "video_transcripts"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    video_interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("video_interviews.id"), nullable=False, index=True
    )

    # Transcript content
    full_transcript: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured transcript (with timestamps and speakers)
    structured_transcript: Mapped[list | None] = mapped_column(JSON)

    # AI model info
    transcription_model: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # Timestamps
    transcribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VideoAnalysis(Base):
    """AI analysis of video interviews (sentiment, keywords, engagement)."""

    __tablename__ = "video_analysis"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    video_interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("video_interviews.id"), nullable=False, index=True
    )

    # Sentiment analysis
    overall_sentiment: Mapped[str | None] = mapped_column(
        String(50)
    )  # positive, neutral, negative
    sentiment_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4)
    )  # -1.00 to 1.00
    sentiment_timeline: Mapped[list | None] = mapped_column(JSON)  # sentiment over time

    # Engagement metrics
    engagement_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    eye_contact_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    speech_pace_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # Keywords and topics
    key_topics: Mapped[list | None] = mapped_column(JSON)
    keywords_extracted: Mapped[list | None] = mapped_column(JSON)

    # Communication analysis
    filler_words_count: Mapped[int | None] = mapped_column(Integer)
    average_response_time: Mapped[float | None] = mapped_column(
        Numeric(10, 2)
    )  # seconds

    # Overall insights
    strengths: Mapped[str | None] = mapped_column(Text)
    areas_for_improvement: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)

    # AI model info
    analysis_model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class VideoHighlight(Base):
    """Key moments and timestamps from video interviews."""

    __tablename__ = "video_highlights"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, nullable=False, autoincrement=True
    )

    video_interview_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("video_interviews.id"), nullable=False, index=True
    )

    # Highlight details
    highlight_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # strong_answer, red_flag, key_moment, technical_discussion
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Timing
    start_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    end_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    # Importance
    importance_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2)
    )  # 0.00 to 1.00

    # AI-generated or manual
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
