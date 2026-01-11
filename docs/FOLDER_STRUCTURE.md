# Folder Structure Guide

## Project Organization

This project follows a modular, scalable architecture with clear separation of concerns:

```
are/
├── api/                          # FastAPI REST API Layer
│   ├── routes/                   # API endpoints
│   │   ├── v1/                   # API version 1
│   │   │   ├── applications.py   # Application management
│   │   │   ├── candidates.py     # Candidate management ✅
│   │   │   ├── jobs.py           # Job postings
│   │   │   ├── offers.py         # Offer management
│   │   │   ├── users.py          # User & auth
│   │   │   ├── webhooks.py       # Webhook handlers
│   │   │   └── agents.py         # Agent endpoints
│   │   └── health.py ✅          # Health checks
│   ├── schemas/                  # Pydantic models
│   │   ├── common.py ✅          # Shared schemas
│   │   ├── candidates.py ✅      # Candidate schemas
│   │   ├── requests.py           # Request models
│   │   └── responses.py          # Response models
│   ├── middleware/               # FastAPI middleware
│   ├── dependencies.py ✅        # DI providers
│   └── main.py ✅                # FastAPI app
│
├── agents/                       # Google ADK AI Agents
│   ├── common/                   # Shared agent utilities ✅
│   │   ├── tools.py ✅           # Shared tools (email extraction, etc.)
│   │   ├── prompts.py ✅         # Shared prompt templates
│   │   └── utils.py ✅           # Shared utilities
│   ├── resume/ ✅                # Resume parsing agent
│   │   ├── agent.py ✅           # ResumeAgent class
│   │   ├── tools.py ✅           # Resume-specific tools
│   │   └── prompts.py ✅         # Resume prompts
│   ├── screening/ ✅             # Application screening agent
│   │   ├── agent.py ✅           # ScreeningAgent class
│   │   ├── tools.py ✅           # Screening tools
│   │   └── prompts.py ✅         # Screening prompts
│   ├── evaluation/ ✅            # Candidate evaluation agent
│   │   ├── agent.py ✅           # EvaluationAgent class
│   │   ├── tools.py ✅           # Evaluation tools
│   │   └── prompts.py ✅         # Evaluation prompts
│   ├── chat/                     # Conversational agent (TODO)
│   │   ├── agent.py              # ChatAgent class
│   │   ├── tools.py              # Chat tools
│   │   └── prompts.py            # Chat prompts
│   ├── email/                    # Email generation agent (TODO)
│   │   ├── agent.py              # EmailAgent class
│   │   ├── tools.py              # Email tools
│   │   └── prompts.py            # Email prompts
│   ├── base.py ✅                # BaseAgent class
│   └── registry.py ✅            # Agent registry
│
├── workers/                      # Celery Background Workers
│   ├── tasks/                    # Task definitions
│   │   ├── documents.py ✅       # Document processing
│   │   ├── emails.py ✅          # Email sending
│   │   ├── embeddings.py ✅      # Vector embeddings
│   │   ├── evaluations.py ✅     # AI evaluations
│   │   └── webhooks.py ✅        # Webhook delivery
│   ├── celery_app.py ✅          # Celery configuration
│   └── worker.py                 # Worker entry point
│
├── core/                         # Core Infrastructure
│   ├── middleware/               # Custom middleware ✅
│   │   ├── logging.py            # Request logging
│   │   ├── error_handling.py    # Error handlers
│   │   └── rate_limiting.py     # Rate limiting
│   ├── storage/                  # File storage
│   │   ├── s3.py                 # AWS S3 storage
│   │   └── local.py              # Local file storage
│   ├── parsers/                  # Document parsers
│   │   ├── document_parser.py   # Main parser
│   │   ├── pdf.py                # PDF parsing
│   │   ├── docx.py               # DOCX parsing
│   │   └── resume.py             # Resume parsing
│   ├── integrations/             # External integrations
│   │   ├── email.py              # SMTP/email service
│   │   ├── calendar.py           # Calendar integration
│   │   └── zoom.py               # Zoom integration
│   ├── utils/                    # Utility functions
│   │   ├── datetime.py           # Date/time helpers
│   │   ├── formatting.py         # Formatting utilities
│   │   └── validators.py         # Validation functions
│   └── config.py ✅              # Pydantic Settings
│
├── database/                     # Database Layer
│   ├── models/                   # SQLAlchemy models
│   │   ├── users.py ✅           # User model
│   │   ├── organizations.py ✅   # Organization model
│   │   ├── candidates.py ✅      # Candidate model
│   │   ├── applications.py ✅    # Application model
│   │   ├── jobs.py ✅            # Job model
│   │   ├── offers.py ✅          # Offer model
│   │   ├── embeddings.py ✅      # Vector embeddings
│   │   └── [17+ more models]    # Other models
│   └── engine.py ✅              # DB engine & sessions
│
├── tests/                        # Test Suite
│   ├── unit/                     # Unit tests ✅
│   │   ├── api/                  # API tests
│   │   ├── agents/               # Agent tests
│   │   ├── workers/              # Worker tests
│   │   └── core/                 # Core tests
│   ├── integration/              # Integration tests ✅
│   └── conftest.py               # Pytest fixtures
│
├── alembic/                      # Database Migrations
│   ├── versions/                 # Migration files
│   └── env.py ✅                 # Alembic config
│
├── docs/                         # Documentation
│   ├── database.md ✅            # Database schema
│   ├── ARCHITECTURE.md ✅        # Architecture guide
│   ├── ARCHITECTURE_VISUAL.md ✅ # Visual diagrams
│   └── IMPLEMENTATION_SUMMARY.md ✅
│
├── .env.example ✅               # Environment template
├── Makefile ✅                   # Development commands
├── README.md ✅                  # Project overview
├── QUICKSTART.md ✅              # Quick setup guide
└── pyproject.toml ✅             # Dependencies
```

## Design Principles

### 1. Agent Organization

Each agent follows a consistent structure:
```
agents/<agent_name>/
├── __init__.py          # Package initialization
├── agent.py             # Main agent class
├── tools.py             # Agent-specific tools
└── prompts.py           # Prompt templates
```

**Shared resources** in `agents/common/`:
- Common tools used across agents
- Shared prompt templates
- Utility functions

### 2. Scalability Features

**Horizontal Scaling:**
- API: Add more FastAPI instances
- Workers: Add more Celery workers per queue
- Agents: Each agent is independent

**Vertical Scaling:**
- Connection pooling for DB
- Redis for caching
- Async I/O throughout

### 3. Maintainability

**Clear Separation:**
- API layer: HTTP concerns only
- Agent layer: AI logic only
- Worker layer: Async tasks only
- Core: Reusable utilities

**Consistent Patterns:**
- All agents extend BaseAgent
- All routes use dependency injection
- All tasks use Celery decorators

**Type Safety:**
- Pydantic for data validation
- Type hints throughout
- MyPy compatible

### 4. Testing Structure

```
tests/
├── unit/                 # Fast, isolated tests
│   ├── api/              # Test API routes
│   ├── agents/           # Test agent logic
│   ├── workers/          # Test tasks
│   └── core/             # Test utilities
└── integration/          # Slower, end-to-end tests
```

## Adding New Components

### Adding a New Agent

1. Create directory: `agents/<agent_name>/`
2. Create files:
   - `__init__.py` - Export agent class
   - `agent.py` - Define agent class extending BaseAgent
   - `tools.py` - Define agent-specific tools
   - `prompts.py` - Define prompt templates
3. Register in `agents/__init__.py`
4. Add tests in `tests/unit/agents/`

Example:
```python
# agents/new_agent/agent.py
from agents.base import BaseAgent
from agents.registry import register_agent

@register_agent("new_agent")
class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="new_agent",
            instructions="Your instructions here",
            tools=[],
        )
    
    async def process(self, input_data):
        # Implementation
        pass
```

### Adding a New API Route

1. Create file in `api/routes/v1/<resource>.py`
2. Define router with FastAPI
3. Add schemas in `api/schemas/`
4. Register in `api/main.py`
5. Add tests

Example:
```python
# api/routes/v1/resource.py
from fastapi import APIRouter, Depends
router = APIRouter(prefix="/resource", tags=["resource"])

@router.get("")
async def list_resources():
    pass
```

### Adding a New Worker Task

1. Add function in `workers/tasks/<category>.py`
2. Decorate with `@celery_app.task`
3. Configure queue routing if needed
4. Add tests

Example:
```python
# workers/tasks/category.py
from workers.celery_app import celery_app

@celery_app.task(name="workers.tasks.category.task_name")
def task_name(arg1, arg2):
    # Implementation
    pass
```

## Best Practices

1. **Keep agents focused**: Each agent should have a single, clear purpose
2. **Share common code**: Use `agents/common/` for shared utilities
3. **Use type hints**: Always provide type annotations
4. **Write tests**: Unit tests for logic, integration tests for workflows
5. **Document**: Add docstrings to all public functions
6. **Use dependencies**: Leverage FastAPI dependency injection
7. **Handle errors**: Proper exception handling and logging
8. **Async all the way**: Use async/await for I/O operations

## Common Patterns

### Agent Usage
```python
from agents.registry import registry

agent = registry.get("resume")
result = await agent.process({"resume_text": text})
```

### Task Queuing
```python
from workers.tasks.documents import parse_resume

task = parse_resume.delay(file_path, candidate_id, org_id)
result = task.get(timeout=30)
```

### Database Access
```python
from api.dependencies import get_db

async def my_route(db: AsyncSession = Depends(get_db)):
    result = await db.execute(query)
```

## File Naming Conventions

- **Python files**: `lowercase_with_underscores.py`
- **Classes**: `PascalCase`
- **Functions**: `lowercase_with_underscores()`
- **Constants**: `UPPERCASE_WITH_UNDERSCORES`
- **Private**: Prefix with underscore `_private_function()`

## Import Organization

```python
# Standard library
import os
from typing import Dict, Any

# Third-party
from fastapi import APIRouter
from sqlalchemy import select

# Local
from core.config import settings
from agents.base import BaseAgent
```

---

✅ = Implemented
❌ = Not implemented (TODO)

This structure is designed to scale from MVP to enterprise while maintaining code quality and developer productivity.
