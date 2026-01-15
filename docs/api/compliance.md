# Compliance API

GDPR and legal compliance endpoints.

> **Important**: These endpoints handle sensitive operations and are subject to additional audit logging.

## Endpoints

### Generate Adverse Action Notice (FCRA)

```http
POST /api/v1/compliance/adverse-action
```

Generate an adverse action notice for rejected candidates.

**Request Body:**
```json
{
  "application_id": 123,
  "reason": "Background check revealed discrepancies",
  "notice_type": "pre"
}
```

**Response:**
```json
{
  "success": true,
  "notice_id": "notice_abc123",
  "content": "Pre-Adverse Action Notice...",
  "sent_at": null
}
```

---

### Verify Work Authorization

```http
POST /api/v1/compliance/work-authorization
```

Verify candidate work authorization.

**Request Body:**
```json
{
  "application_id": 123,
  "document_type": "work_visa",
  "document_number": "A12345678",
  "expiry_date": "2025-12-31"
}
```

---

### Generate EEO Report

```http
GET /api/v1/compliance/eeo-report?start_date=2024-01-01&end_date=2024-12-31
```

Generate an Equal Employment Opportunity report.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| start_date | string | Yes | Start date (YYYY-MM-DD) |
| end_date | string | Yes | End date (YYYY-MM-DD) |
| job_id | integer | No | Filter by job |

---

### Export User Data (DSAR)

```http
GET /api/v1/compliance/data-export/{user_id}
```

Export all data for a user (Data Subject Access Request).

**Response:**
```json
{
  "user": {...},
  "applications": [...],
  "interviews": [...],
  "communications": [...],
  "consent_history": [...]
}
```

---

### Erase User Data (Right to be Forgotten)

```http
DELETE /api/v1/compliance/data-erasure/{user_id}
```

Permanently delete all user data.

> **Warning**: This action is irreversible and will be logged.

**Response:**
```json
{
  "success": true,
  "records_deleted": 42,
  "confirmation_id": "erasure_abc123"
}
```
