# Database Schema

Comprehensive database schema for the Applicant Recruitment Engine (ARE) with AI-powered features.

## Structure

### Core Models
- `users.py` - User authentication and profiles
- `organizations.py` - Organization management
- `files.py` - File storage and metadata
- `subscription.py` - Subscription and billing

### Recruitment Models
- `jobs.py` - Job postings and requirements
- `candidates.py` - Candidate profiles and history
- `applications.py` - Application tracking
- `interviews.py` - Interview scheduling and feedback
- `assessments.py` - Skills assessments

### AI-Powered Features
- `ai_evaluations.py` - AI candidate evaluations
- `ai_assessments_ext.py` - Advanced AI assessments (proctoring, adaptive testing)
- `deep_evaluations.py` - Portfolio and comprehensive evaluation
- `chat_sessions.py` - AI chat and messaging
- `video_interviews.py` - Video interview analysis
- `embeddings.py` - Vector search (pgvector)

### Supporting Models
- `communications.py` - Email and notifications
- `audit.py` - Audit trails and compliance

### Utilities
- `security.py` - GDPR/SOC 2 compliance utilities
- `relationships.py` - SQLAlchemy relationships
- `engine.py` - Database engine configuration

## Features

- **68+ Tables** across all modules
- **GDPR & SOC 2 Compliant** with data classification
- **Vector Search** using pgvector for semantic matching
- **AI Integration** for evaluations, screening, and analysis
- **Flexible JSON Storage** for custom evaluation criteria
- **Comprehensive Audit Trails** for all operations

## Setup

1. Install pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Run migrations:
```bash
alembic upgrade head
```

3. Create vector indexes:
```sql
CREATE INDEX ON embeddings USING ivfflat (embedding_vector vector_cosine_ops);
```

## Compliance

All models include:
- PII field markers
- GDPR data categories
- Retention periods
- Encryption requirements
- Anonymization support

See `security.py` for compliance utilities.
