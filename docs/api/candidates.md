# Candidates API

Manage candidates and their applications.

> **GDPR Note**: This API handles PII. All access is logged for audit purposes.

## Endpoints

### List Candidates

```http
GET /api/v1/candidates?job_id=123&stage=interview
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | integer | Yes | Job ID to list candidates for |
| stage | string | No | Filter by stage |
| search | string | No | Search by name or email |
| page | integer | No | Page number (default: 1) |
| page_size | integer | No | Items per page (default: 20) |

**Response:**
```json
{
  "items": [
    {
      "application_id": 123,
      "candidate_id": 456,
      "name": "Jane Doe",
      "email": "j***@example.com",
      "stage": "interview",
      "ai_score": 0.85
    }
  ],
  "total": 42,
  "page": 1,
  "pages": 3
}
```

---

### Get Candidate Details

```http
GET /api/v1/candidates/{application_id}
```

Get full candidate profile for an application.

**Response:**
```json
{
  "application_id": 123,
  "candidate_id": 456,
  "name": "Jane Doe",
  "email": "jane@example.com",
  "phone": "+1-555-0123",
  "skills": ["Python", "React"],
  "experience_years": 5,
  "education": [...],
  "experience": [...]
}
```

---

### Shortlist Candidate

```http
POST /api/v1/candidates/{application_id}/shortlist
```

Shortlist a candidate.

**Request Body:**
```json
{
  "reason": "Strong technical skills and culture fit"
}
```

---

### Reject Candidate

```http
POST /api/v1/candidates/{application_id}/reject
```

Reject a candidate.

**Request Body:**
```json
{
  "reason": "Does not meet minimum experience requirements",
  "send_notification": true
}
```

---

### Get Candidate Documents

```http
GET /api/v1/candidates/{application_id}/documents
```

Get all documents for a candidate.

**Response:**
```json
{
  "resume": {...},
  "cover_letter": {...},
  "portfolio": [...]
}
```

---

### Bulk Upload Resumes

```http
POST /api/v1/candidates/bulk-upload?job_id=123
Content-Type: multipart/form-data
```

Upload multiple resumes at once.

**Request:**
- `files`: Multiple resume files
- `job_id`: Target job ID

**Response:**
```json
{
  "message": "Bulk upload queued",
  "task_id": "bulk_abc123",
  "files_queued": 25
}
```
