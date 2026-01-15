# Agents API

The Agents API provides access to the AI Hiring Copilot functionality.

## Endpoints

### Chat with Copilot

```http
POST /api/v1/agents/chat
```

Chat with the AI hiring copilot using natural language.

**Request Body:**
```json
{
  "query": "Find me React developers with 5+ years experience",
  "session_id": "session_abc123",
  "context": {
    "job_id": 42
  }
}
```

**Response:**
```json
{
  "text": "I found 12 React developers matching your criteria...",
  "tools_used": [
    {
      "tool_name": "search_candidates",
      "tool_args": {"query": "React developers 5+ years"},
      "tool_result": {"count": 12}
    }
  ],
  "sources": []
}
```

---

### Parse Resume

```http
POST /api/v1/agents/resume/parse
Content-Type: multipart/form-data
```

Upload and parse a resume file.

**Request:**
- `file`: Resume file (PDF, DOCX)

**Response:**
```json
{
  "success": true,
  "parsed_data": {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "skills": ["Python", "React", "AWS"],
    "experience": [...]
  }
}
```

---

### Trigger Evaluation

```http
POST /api/v1/agents/evaluations/conduct
```

Trigger an AI evaluation for an application.

**Request Body:**
```json
{
  "application_id": 123,
  "type": "full"
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "eval_abc123",
  "message": "Full evaluation initiated."
}
```

---

### Generate Interview Questions

```http
POST /api/v1/agents/interviews/generate-questions
```

Generate tailored interview questions.

**Request Body:**
```json
{
  "application_id": 123,
  "interview_type": "technical",
  "focus_areas": ["system design", "algorithms"]
}
```

**Response:**
```json
{
  "questions": [
    "Describe a time when you designed a scalable system...",
    "How would you approach optimizing a slow database query?"
  ],
  "context": "Questions tailored for Senior Backend Engineer role"
}
```
