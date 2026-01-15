# Alethic API Reference

Welcome to the Alethic API documentation. This API powers the AI Hiring Copilot platform.

## Base URL

```
https://api.alethic.ai/api/v1
```

## Authentication

All API requests require a valid JWT token in the Authorization header:

```
Authorization: Bearer <your_token>
```

See [Authentication Guide](./authentication.md) for details on obtaining tokens.

## Rate Limiting

| Tier | Requests/Second | Requests/Minute | Requests/Hour |
|------|-----------------|-----------------|---------------|
| Standard | 10 | 100 | 1,000 |
| AI Operations | 2 | 10 | 100 |

## GDPR & Compliance

All endpoints handling PII are:
- Logged for audit purposes
- Subject to data retention policies
- Available for DSAR exports via `/compliance/data-export`

## API Sections

- [Agents](./agents.md) - AI Copilot chat and actions
- [Candidates](./candidates.md) - Candidate management
- [Applications](./applications.md) - Application workflow
- [Jobs](./jobs.md) - Job postings
- [Interviews](./interviews.md) - Interview scheduling
- [Evaluations](./evaluations.md) - AI evaluations
- [Documents](./documents.md) - Resume and documents
- [Search](./search.md) - Semantic search
- [Bulk Operations](./bulk.md) - Bulk actions
- [Background Checks](./background-checks.md) - Background verification
- [Compliance](./compliance.md) - GDPR & legal compliance
- [Calendar](./calendar.md) - Scheduling
- [Comparison](./comparison.md) - Candidate comparison

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "request_id": "abc123"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Error |
