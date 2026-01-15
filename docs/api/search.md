# Search API

Semantic (AI-powered) candidate search.

## Endpoints

### Semantic Search

```http
POST /api/v1/search/semantic
```

Search candidates using natural language.

**Request Body:**
```json
{
  "query": "Python developers with machine learning experience",
  "job_id": 123,
  "limit": 20,
  "filters": {
    "min_experience": 3,
    "location": "Remote"
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "application_id": 456,
      "name": "Jane Doe",
      "match_score": 0.92,
      "highlights": ["5 years Python", "TensorFlow expert"]
    }
  ],
  "total": 15,
  "query_embedding_id": "emb_abc123"
}
```

---

### Find Similar Candidates

```http
GET /api/v1/search/similar/{application_id}?limit=10
```

Find candidates similar to a given application.

---

### Match Candidates to Job

```http
GET /api/v1/search/match/{job_id}?limit=20&min_score=0.7
```

Find best matching candidates using vector similarity.
