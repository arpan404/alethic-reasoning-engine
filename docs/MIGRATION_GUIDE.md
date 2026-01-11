# Updated Folder Structure - Migration Guide

## Summary of Changes

The folder structure has been completely reorganized for better scalability, maintainability, and developer experience.

## Key Improvements

### 1. **Agent Organization** ✅

**Before:**
```
agents/
├── resume/agent.py, tools.py
├── screening/agent.py, tools.py
└── Other agent folders (empty or inconsistent)
```

**After:**
```
agents/
├── common/              # NEW: Shared utilities
│   ├── tools.py         # Common extraction tools
│   ├── prompts.py       # Shared prompt templates
│   └── utils.py         # Utility functions
├── resume/              # Consistent structure
│   ├── agent.py         # Agent class
│   ├── tools.py         # Resume-specific tools
│   └── prompts.py       # NEW: Resume prompts
├── screening/           # Consistent structure
│   ├── agent.py
│   ├── tools.py
│   └── prompts.py       # NEW: Screening prompts
├── evaluation/          # NEW: Fully implemented
│   ├── agent.py         # EvaluationAgent
│   ├── tools.py         # Evaluation tools
│   └── prompts.py       # Evaluation prompts
├── chat/                # NEW: Structure ready
│   ├── agent.py
│   ├── tools.py
│   └── prompts.py
└── email/               # NEW: Structure ready
    ├── agent.py
    ├── tools.py
    └── prompts.py
```

**Benefits:**
- Consistent structure across all agents
- Shared code in `agents/common/`
- Prompt templates separated from code
- Easy to add new agents

### 2. **Core Infrastructure** ✅

**New Additions:**
```
core/
└── middleware/          # NEW: Custom middleware
    ├── logging.py       # Request logging
    ├── error_handling.py # Error handlers
    └── rate_limiting.py  # Rate limiting
```

### 3. **Test Organization** ✅

**Before:**
```
tests/
├── conftest.py
├── test_document_parser.py
└── test_s3.py
```

**After:**
```
tests/
├── unit/                # NEW: Unit tests
│   ├── api/             # API route tests
│   ├── agents/          # Agent logic tests
│   ├── workers/         # Task tests
│   └── core/            # Core utility tests
└── integration/         # NEW: E2E tests
```

### 4. **Documentation** ✅

**New Files:**
- `FOLDER_STRUCTURE.md` - Complete structure guide
- `QUICKSTART.md` - 5-minute setup
- `docs/ARCHITECTURE_VISUAL.md` - Visual diagrams
- `docs/IMPLEMENTATION_SUMMARY.md` - What we built

### 5. **Development Tools** ✅

- `.gitkeep` files in empty directories
- Proper `__init__.py` files with exports
- Consistent naming conventions

## New Features

### 1. Shared Agent Tools (`agents/common/tools.py`)

Extract common information across agents:
```python
from agents.common.tools import (
    extract_email,
    extract_phone,
    extract_linkedin_url,
    parse_date,
    calculate_duration,
)
```

### 2. Shared Prompt Templates (`agents/common/prompts.py`)

Reusable prompt components:
```python
from agents.common.prompts import (
    PROFESSIONAL_TONE,
    ANALYTICAL_TONE,
    EVALUATION_CRITERIA,
    SCORING_GUIDELINES,
)
```

### 3. Agent Utilities (`agents/common/utils.py`)

Helper functions:
```python
from agents.common.utils import (
    parse_json_response,
    validate_agent_output,
    chunk_text,
    calculate_confidence_score,
)
```

### 4. Evaluation Agent (`agents/evaluation/`)

New comprehensive evaluation agent:
```python
from agents.registry import registry

agent = registry.get("evaluation")
result = await agent.process({
    "candidate_profile": {...},
    "job_requirements": {...},
    "company_culture": {...},
})
```

## Usage Examples

### Using Shared Tools

```python
# Old way - duplicated code in each agent
def extract_email(text):
    # Email extraction logic
    pass

# New way - use shared tools
from agents.common.tools import extract_email

email = extract_email(resume_text)
phone = extract_phone(resume_text)
linkedin = extract_linkedin_url(resume_text)
```

### Using Shared Prompts

```python
# Old way - prompts hardcoded in agent
instructions = "You are an expert..."

# New way - use shared templates
from agents.resume.prompts import RESUME_PARSER_SYSTEM_PROMPT

instructions = RESUME_PARSER_SYSTEM_PROMPT
```

### Agent Registration

All agents are auto-registered:
```python
from agents.registry import registry

# Get any registered agent
resume_agent = registry.get("resume")
screening_agent = registry.get("screening")
evaluation_agent = registry.get("evaluation")

# List all agents
all_agents = registry.list_agents()
```

## Migration Checklist

For existing code that needs updating:

- [ ] Update imports to use `agents.common` where applicable
- [ ] Move hardcoded prompts to respective `prompts.py` files
- [ ] Move shared logic to `agents/common/tools.py`
- [ ] Update tests to use new structure
- [ ] Add type hints to all functions
- [ ] Add docstrings to public functions

## File Organization Rules

1. **One agent per directory**: Each agent has its own folder
2. **Consistent file names**: `agent.py`, `tools.py`, `prompts.py`
3. **Shared code in common/**: Don't duplicate logic
4. **Type hints everywhere**: Use type annotations
5. **Docstrings required**: Document all public functions

## Adding a New Agent

Template for creating a new agent:

```bash
# 1. Create directory structure
mkdir -p agents/my_agent
touch agents/my_agent/__init__.py
touch agents/my_agent/agent.py
touch agents/my_agent/tools.py
touch agents/my_agent/prompts.py
```

```python
# 2. agents/my_agent/prompts.py
"""My agent prompt templates."""

SYSTEM_PROMPT = """You are an expert in..."""

# 3. agents/my_agent/tools.py
"""Tools for my agent."""

def my_tool(input_data):
    """Tool description."""
    pass

# 4. agents/my_agent/agent.py
"""My agent implementation."""

from agents.base import BaseAgent
from agents.registry import register_agent
from agents.my_agent.tools import my_tool
from agents.my_agent.prompts import SYSTEM_PROMPT

@register_agent("my_agent")
class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="my_agent",
            instructions=SYSTEM_PROMPT,
            tools=[my_tool],
        )
    
    async def process(self, input_data):
        # Implementation
        pass

# 5. Update agents/__init__.py
from agents.my_agent.agent import MyAgent

__all__ = [..., "MyAgent"]
```

## Breaking Changes

None! All existing functionality is preserved. The changes are purely organizational.

## Benefits Summary

✅ **Scalability**: Easy to add new agents and features
✅ **Maintainability**: Clear structure, shared code, no duplication
✅ **Type Safety**: Comprehensive type hints throughout
✅ **Testability**: Organized test structure
✅ **Documentation**: Comprehensive guides and examples
✅ **Developer Experience**: Consistent patterns, easy to navigate

## Next Steps

1. Review the new structure in `FOLDER_STRUCTURE.md`
2. Check out shared utilities in `agents/common/`
3. Use the evaluation agent for comprehensive assessments
4. Add your custom agents following the template
5. Write tests in the `tests/unit/` and `tests/integration/` structure

## Questions?

Refer to:
- `FOLDER_STRUCTURE.md` - Complete structure guide
- `QUICKSTART.md` - Getting started
- `ARCHITECTURE.md` - Detailed architecture
- `README.md` - Project overview
