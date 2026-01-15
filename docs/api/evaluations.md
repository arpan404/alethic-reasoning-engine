# Evaluations API

AI-powered candidate evaluations.

## Endpoints

### Get Pre-Evaluation

```http
GET /api/v1/evaluations/{application_id}/pre
```

Get quick screening results.

**Response:**
```json
{
  "application_id": 123,
  "status": "completed",
  "recommendation": "proceed",
  "scores": {
    "skills_match": 0.85,
    "experience_match": 0.72
  },
  "summary": "Strong technical background..."
}
```

---

### Get Full Evaluation

```http
GET /api/v1/evaluations/{application_id}/full
```

Get comprehensive evaluation.

---

### Get Prescreening

```http
GET /api/v1/evaluations/{application_id}/prescreening
```

Get AI prescreening (pass/fail) results.

---

### Trigger Evaluation

```http
POST /api/v1/evaluations/{application_id}/trigger?evaluation_type=full
```

Trigger an AI evaluation.

---

### Get Rankings

```http
GET /api/v1/evaluations/rankings?job_id=123&limit=10
```

Get AI-ranked candidates for a job.
