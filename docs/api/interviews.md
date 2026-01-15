# Interviews API

Interview scheduling and management.

## Endpoints

### Schedule Interview

```http
POST /api/v1/interviews/schedule
```

Schedule an interview.

**Request Body:**
```json
{
  "application_id": 123,
  "interview_type": "technical",
  "scheduled_at": "2024-01-20T14:00:00Z",
  "duration_minutes": 60,
  "interviewer_ids": [10, 11]
}
```

**Response:**
```json
{
  "success": true,
  "interview_id": 789,
  "meeting_link": "https://zoom.us/j/123456",
  "calendar_event_id": "evt_abc123"
}
```

---

### List Interviews

```http
GET /api/v1/interviews?job_id=123&status=scheduled
```

List interviews with filtering.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| application_id | integer | Filter by application |
| job_id | integer | Filter by job |
| status | string | Filter by status |
| start_date | datetime | Start range |
| end_date | datetime | End range |
