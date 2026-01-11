# Koru ATS - Architecture Visualization

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  (React/Vue/Mobile App - External, not in this codebase)       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│                         Port: 8000                               │
├─────────────────────────────────────────────────────────────────┤
│  api/main.py - FastAPI Application                              │
│  ├── CORS Middleware                                             │
│  ├── Authentication (JWT)                                        │
│  └── Routes:                                                     │
│      ├── /health         → Health Check                          │
│      ├── /api/v1/candidates → Candidate CRUD                     │
│      ├── /api/v1/applications → Application CRUD                 │
│      ├── /api/v1/jobs → Job Posting CRUD                         │
│      ├── /api/v1/offers → Offer Management                       │
│      ├── /api/v1/users → Auth & User Management                  │
│      ├── /api/v1/webhooks → Webhook Handlers                     │
│      └── /api/v1/agents → Agent Interactions                     │
└────────────┬──────────────────────────┬─────────────────────────┘
             │                          │
             │ Call Agents              │ Database Queries
             ▼                          ▼
┌──────────────────────┐    ┌──────────────────────────┐
│   AGENT LAYER        │    │   DATABASE LAYER         │
│   (Google ADK)       │    │   (PostgreSQL + Vector)  │
├──────────────────────┤    ├──────────────────────────┤
│ agents/base.py       │    │ database/engine.py       │
│ agents/registry.py   │    │ ├── SQLAlchemy 2.0 Async │
│                      │    │ ├── Connection Pooling   │
│ Agents:              │    │ └── pgvector Extension   │
│ ├── Resume Parser    │    │                          │
│ │   └── Extract      │    │ Models (20+ tables):     │
│ │       structured   │    │ ├── users                │
│ │       data         │    │ ├── organizations        │
│ ├── Screening Agent  │    │ ├── candidates           │
│ │   └── Score & eval │    │ ├── applications         │
│ ├── Evaluation       │    │ ├── jobs                 │
│ │   └── AI assess    │    │ ├── offers               │
│ └── Chat Agent       │    │ ├── interviews           │
│     └── Conversati.. │    │ ├── embeddings (vector)  │
│                      │    │ └── 140+ Indexes         │
│ Google Gemini 2.0    │    │     ├── Basic            │
│                      │    │     ├── Composite        │
└──────────────────────┘    │     ├── GIN (JSONB)      │
                            │     ├── Partial          │
                            │     └── HNSW (vectors)   │
                            └──────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   TASK QUEUE LAYER (Celery)                      │
├─────────────────────────────────────────────────────────────────┤
│  workers/celery_app.py - Celery Application                      │
│  ├── Broker: Redis                                               │
│  ├── Backend: Redis                                              │
│  └── Queues:                                                     │
│      ├── high_priority (p:10) → Evaluations                      │
│      ├── webhooks (p:8)       → Webhook delivery                 │
│      ├── documents (p:7)      → Resume parsing                   │
│      ├── emails (p:6)         → Email sending                    │
│      └── default (p:5)        → General tasks                    │
├─────────────────────────────────────────────────────────────────┤
│  Task Types:                                                     │
│  ├── workers/tasks/documents.py                                  │
│  │   ├── parse_resume                                            │
│  │   ├── generate_document                                       │
│  │   └── batch_process_resumes                                   │
│  ├── workers/tasks/emails.py                                     │
│  │   ├── send_email                                              │
│  │   ├── send_bulk_emails                                        │
│  │   └── send_campaign_email                                     │
│  ├── workers/tasks/embeddings.py                                 │
│  │   ├── generate_resume_embedding                               │
│  │   ├── generate_job_embedding                                  │
│  │   └── similarity_search                                       │
│  ├── workers/tasks/evaluations.py                                │
│  │   ├── evaluate_candidate                                      │
│  │   ├── screen_application                                      │
│  │   └── generate_interview_questions                            │
│  └── workers/tasks/webhooks.py                                   │
│      ├── deliver_webhook                                         │
│      └── process_inbound_webhook                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      CORE UTILITIES                              │
├─────────────────────────────────────────────────────────────────┤
│  core/config.py - Pydantic Settings (Environment Variables)      │
│  ├── Database configuration                                      │
│  ├── Redis configuration                                         │
│  ├── S3 configuration                                            │
│  ├── Google AI configuration                                     │
│  ├── JWT configuration                                           │
│  └── Email configuration                                         │
├─────────────────────────────────────────────────────────────────┤
│  core/storage/                                                   │
│  ├── s3.py - AWS S3 storage                                      │
│  └── local.py - Local file storage                               │
├─────────────────────────────────────────────────────────────────┤
│  core/parsers/                                                   │
│  ├── document_parser.py - Main parser                            │
│  ├── pdf.py - PDF parsing                                        │
│  ├── docx.py - DOCX parsing                                      │
│  └── resume.py - Resume-specific parsing                         │
├─────────────────────────────────────────────────────────────────┤
│  core/integrations/                                              │
│  ├── email.py - SMTP/SendGrid                                    │
│  ├── calendar.py - Google/Outlook Calendar                       │
│  └── zoom.py - Zoom integration                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐  │
│  │   Redis     │  │ AWS S3   │  │ Google  │  │   SMTP       │  │
│  │             │  │          │  │ Gemini  │  │   Server     │  │
│  │ Task Broker │  │ File     │  │ 2.0 API │  │   Email      │  │
│  │ & Backend   │  │ Storage  │  │         │  │   Delivery   │  │
│  └─────────────┘  └──────────┘  └─────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Request Flow Examples

### 1. Resume Upload & Parsing Flow

```
User uploads resume
    ↓
[POST /api/v1/candidates]
    ├─ Create candidate record in DB
    ├─ Upload file to S3
    └─ Queue task: parse_resume.delay()
        ↓
    [Celery Worker: documents queue]
        ├─ Download file from S3
        ├─ Call Resume Agent
        │   └─ Google Gemini extracts structured data
        ├─ Save parsed data to DB
        └─ Queue task: generate_resume_embedding.delay()
            ↓
        [Celery Worker: documents queue]
            ├─ Call embedding model
            └─ Store vector in embeddings table
```

### 2. Candidate Screening Flow

```
Application submitted
    ↓
[POST /api/v1/applications]
    ├─ Create application record
    └─ Queue task: screen_application.delay()
        ↓
    [Celery Worker: high_priority queue]
        ├─ Fetch candidate data
        ├─ Fetch job requirements
        ├─ Call Screening Agent
        │   ├─ Google Gemini evaluates fit
        │   ├─ Calculates fit score
        │   └─ Generates recommendations
        ├─ Save evaluation to DB
        └─ Send notification email
```

### 3. Job Matching Flow

```
User searches for candidates
    ↓
[GET /api/v1/jobs/{id}/matches]
    ├─ Generate query embedding
    └─ Query task: similarity_search.delay()
        ↓
    [Celery Worker: documents queue]
        ├─ Perform pgvector similarity search
        │   SELECT * FROM embeddings
        │   ORDER BY embedding <-> query_embedding
        │   LIMIT 50
        ├─ Fetch candidate details
        └─ Return ranked matches
```

## Data Flow Diagram

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ HTTP Request
     ▼
┌────────────────┐
│   FastAPI      │
│   Endpoints    │
└─────┬──────────┘
      │
      ├─────────► Authentication (JWT)
      │
      ├─────────► Request Validation (Pydantic)
      │
      ├─────────► Database Operations (SQLAlchemy)
      │           ├─ Read (SELECT with joins)
      │           ├─ Write (INSERT/UPDATE)
      │           └─ Vector Search (pgvector)
      │
      ├─────────► Agent Calls (Google ADK)
      │           ├─ Resume parsing
      │           ├─ Screening
      │           └─ Evaluation
      │
      └─────────► Task Queuing (Celery)
                  ├─ Async processing
                  ├─ Background jobs
                  └─ Scheduled tasks
```

## Technology Stack

### Backend Framework
- **FastAPI** 0.115+ - Modern async Python web framework
- **Uvicorn** - ASGI server with auto-reload
- **Pydantic** 2.9+ - Data validation and settings

### AI & Agents
- **Google ADK** 1.21+ - Agent Development Kit
- **Google Gemini** 2.0 - Large language model

### Task Queue
- **Celery** 5.3+ - Distributed task queue
- **Redis** 6+ - Message broker and result backend

### Database
- **PostgreSQL** 14+ - Primary database
- **SQLAlchemy** 2.0+ - ORM with async support
- **pgvector** - Vector similarity search
- **Alembic** - Database migrations

### Storage & Cloud
- **aioboto3** - Async AWS SDK (S3)
- **AWS S3** - File storage

### Authentication
- **python-jose** - JWT token handling
- **passlib** - Password hashing

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      PRODUCTION                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐   │
│  │  Nginx   │────────▶│ FastAPI  │────────▶│PostgreSQL│   │
│  │  (LB)    │         │  (3x)    │         │  Primary │   │
│  └──────────┘         └──────────┘         └──────────┘   │
│       │                                           │         │
│       │               ┌──────────┐                │         │
│       └──────────────▶│  Celery  │────────────────┘         │
│                       │ Workers  │                          │
│                       │  (5x)    │                          │
│                       └────┬─────┘                          │
│                            │                                │
│                       ┌────▼─────┐                          │
│                       │  Redis   │                          │
│                       │ Cluster  │                          │
│                       └──────────┘                          │
│                                                             │
│  External Services:                                         │
│  - AWS S3 (File Storage)                                    │
│  - Google AI (Gemini API)                                   │
│  - SMTP Server (Email)                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Features

### Horizontal Scaling
- **API**: Add more FastAPI instances behind load balancer
- **Workers**: Add more Celery workers per queue
- **Database**: Read replicas for query distribution

### Performance Optimization
- **Indexes**: 140+ strategic database indexes
- **Connection Pooling**: Configured for API and workers
- **Async I/O**: Non-blocking operations throughout
- **Caching**: Redis available for caching layers

### Reliability
- **Health Checks**: `/health` and `/ready` endpoints
- **Task Retries**: Configurable retry logic with backoff
- **Queue Priorities**: Critical tasks process first
- **Graceful Shutdown**: Proper cleanup of connections

## Security Features

### Authentication & Authorization
- JWT token-based authentication
- Role-based access control (RBAC)
- Secure password hashing (bcrypt)

### Data Protection
- Input validation with Pydantic
- SQL injection prevention (parameterized queries)
- CORS configuration for API access
- Environment-based secrets management

### Audit & Compliance
- Audit trail in database
- Request/response logging
- Error tracking (Sentry-ready)

---

**This architecture provides a solid foundation for a scalable, maintainable ATS platform.**
