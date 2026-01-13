# Beta Registration System

## Overview

The beta registration system allows users to apply for early access to the platform's beta features. The system manages registrations, tracks status through the approval workflow, and provides admin endpoints for managing registrations.

## Database Schema

### BetaRegistration Table

```sql
CREATE TABLE beta_registrations (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    company_name VARCHAR(255),
    job_title VARCHAR(100),
    phone VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    use_case TEXT,
    referral_source VARCHAR(100),
    newsletter_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP
);

-- Indices for performance
CREATE INDEX idx_beta_registrations_email ON beta_registrations(email);
CREATE INDEX idx_beta_status_created ON beta_registrations(status, created_at);
CREATE INDEX idx_beta_email_status ON beta_registrations(email, status);
```

## Status Values

- **pending**: Initial registration awaiting review (default)
- **approved**: Approved for beta access
- **rejected**: Not approved for beta access
- **active**: Currently using beta features
- **inactive**: No longer using beta features

## API Endpoints

### 1. Register for Beta (Public)

**POST** `/api/v1/beta/register`

Register a new user for the beta program.

**Request Body:**
```json
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Tech Corp",
  "job_title": "Hiring Manager",
  "phone": "+1-555-0123",
  "use_case": "We want to streamline our recruiting process",
  "referral_source": "Product Hunt",
  "newsletter_opt_in": true
}
```

**Required Fields:**
- `email` (EmailStr): User's email address
- `first_name` (str, 1-100 chars)
- `last_name` (str, 1-100 chars)

**Optional Fields:**
- `company_name` (str, max 255 chars)
- `job_title` (str, max 100 chars)
- `phone` (str, max 20 chars)
- `use_case` (str, max 2000 chars): Describe intended use
- `referral_source` (str, max 100 chars): How they found out
- `newsletter_opt_in` (bool): Newsletter subscription consent

**Response (201 Created):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Tech Corp",
  "job_title": "Hiring Manager",
  "phone": "+1-555-0123",
  "status": "pending",
  "use_case": "We want to streamline our recruiting process",
  "referral_source": "Product Hunt",
  "newsletter_opt_in": true,
  "approved_at": null,
  "created_at": "2026-01-13T12:00:00Z",
  "updated_at": "2026-01-13T12:00:00Z"
}
```

**Error Responses:**
- `409 Conflict`: Email already registered
- `400 Bad Request`: Validation error (missing required fields or invalid format)

---

### 2. Get Registration (Admin)

**GET** `/api/v1/beta/{registration_id}`

Retrieve a specific beta registration by ID.

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Tech Corp",
  "job_title": "Hiring Manager",
  "phone": "+1-555-0123",
  "status": "pending",
  "use_case": "We want to streamline our recruiting process",
  "referral_source": "Product Hunt",
  "newsletter_opt_in": true,
  "approved_at": null,
  "created_at": "2026-01-13T12:00:00Z",
  "updated_at": "2026-01-13T12:00:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Registration not found

---

### 3. Update Registration Status (Admin)

**PATCH** `/api/v1/beta/{registration_id}`

Update the status and approval timestamp of a registration.

**Request Body:**
```json
{
  "status": "approved",
  "approved_at": "2026-01-13T13:30:00Z"
}
```

**Fields:**
- `status` (str): New status (pending, approved, rejected, active, inactive)
- `approved_at` (datetime, optional): When approved (auto-set to now if omitted and status is approved)

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Tech Corp",
  "job_title": "Hiring Manager",
  "phone": "+1-555-0123",
  "status": "approved",
  "use_case": "We want to streamline our recruiting process",
  "referral_source": "Product Hunt",
  "newsletter_opt_in": true,
  "approved_at": "2026-01-13T13:30:00Z",
  "created_at": "2026-01-13T12:00:00Z",
  "updated_at": "2026-01-13T13:30:00Z"
}
```

**Error Responses:**
- `404 Not Found`: Registration not found
- `400 Bad Request`: Invalid status value

---

### 4. List All Registrations (Admin)

**GET** `/api/v1/beta`

Get paginated list of all beta registrations.

**Query Parameters:**
- `page` (int, default: 1): Page number (≥ 1)
- `page_size` (int, default: 20, max: 100): Items per page
- `status_filter` (str, optional): Filter by status (pending, approved, rejected, active, inactive)

**Example:**
```
GET /api/v1/beta?page=1&page_size=20&status_filter=pending
```

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "email": "user1@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "company_name": "Tech Corp",
      "job_title": "Hiring Manager",
      "phone": "+1-555-0123",
      "status": "pending",
      "use_case": "Streamline recruiting",
      "referral_source": "Product Hunt",
      "newsletter_opt_in": true,
      "approved_at": null,
      "created_at": "2026-01-13T12:00:00Z",
      "updated_at": "2026-01-13T12:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**Error Responses:**
- `400 Bad Request`: Invalid status_filter or pagination parameters

---

### 5. Delete Registration (Admin)

**DELETE** `/api/v1/beta/{registration_id}`

Delete a beta registration.

**Response (204 No Content)**

**Error Responses:**
- `404 Not Found`: Registration not found

---

## File Structure

```
database/
  models/
    beta_registrations.py    # BetaRegistration model & BetaStatus enum
api/
  schemas/
    beta.py                  # Pydantic schemas
  routes/
    v1/
      beta.py                # API endpoints
alembic/
  versions/
    001_add_beta_registrations.py  # Database migration
```

## Model Classes

### BetaRegistration (SQLAlchemy Model)

Located in `database/models/beta_registrations.py`

**Attributes:**
- `id` (int): Primary key
- `email` (str): Unique user email
- `first_name` (str): User's first name
- `last_name` (str): User's last name
- `company_name` (str, nullable): Company name
- `job_title` (str, nullable): Job title
- `phone` (str, nullable): Phone number
- `status` (BetaStatus): Current registration status
- `use_case` (str, nullable): Intended use description
- `referral_source` (str, nullable): How they found out
- `newsletter_opt_in` (bool): Newsletter subscription preference
- `created_at` (datetime): Registration creation timestamp
- `updated_at` (datetime): Last update timestamp
- `approved_at` (datetime, nullable): When approved

### BetaStatus (Enum)

```python
class BetaStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    INACTIVE = "inactive"
```

---

## Pydantic Schemas

Located in `api/schemas/beta.py`

### BetaRegistrationRequest
Used for creating new registrations (POST /register)

### BetaRegistrationResponse
Used in all response bodies, includes timestamps

### BetaRegistrationUpdate
Used for updating registration status (PATCH /{id})

---

## Database Migration

Migration file: `alembic/versions/001_add_beta_registrations.py`

To run the migration:

```bash
# Using Alembic
alembic upgrade head

# Or using Python
python -c "from database.engine import init_db; import asyncio; asyncio.run(init_db())"
```

The migration creates:
1. `beta_registrations` table with all columns
2. Unique constraint on email
3. Three performance indices:
   - `idx_beta_registrations_email`: For email lookups
   - `idx_beta_status_created`: For filtering by status and sorting by creation date
   - `idx_beta_email_status`: For combined email/status queries

---

## Integration Points

The beta registration system integrates with:

1. **Database**: Uses SQLAlchemy ORM with async support
2. **API**: FastAPI router included in `api/main.py`
3. **Security**: ComplianceMixin for GDPR compliance (when extended)
4. **Logging**: Audit trail via `@audit_changes` decorator

---

## Usage Examples

### Register for Beta (JavaScript/Fetch)

```javascript
const response = await fetch('/api/v1/beta/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    first_name: 'John',
    last_name: 'Doe',
    company_name: 'Tech Corp',
    job_title: 'Hiring Manager',
    use_case: 'Streamline our recruiting process',
    referral_source: 'Product Hunt',
    newsletter_opt_in: true
  })
});

const registration = await response.json();
console.log('Registration ID:', registration.id);
```

### List Pending Registrations (Python)

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        '/api/v1/beta',
        params={'status_filter': 'pending', 'page_size': 50}
    )
    data = response.json()
    print(f"Found {data['total']} pending registrations")
```

### Approve Registration (cURL)

```bash
curl -X PATCH 'http://localhost:8000/api/v1/beta/1' \
  -H 'Content-Type: application/json' \
  -d '{"status": "approved"}'
```

---

## Future Enhancements

1. **Email Notifications**: Send confirmation and approval emails
2. **Webhook Integration**: Notify external systems when status changes
3. **Analytics**: Track conversion rates, sources, use cases
4. **Auto-Approval**: Rules engine for automatic approval
5. **Bulk Operations**: CSV export/import of registrations
6. **Integration with Users**: Auto-create User account when approved
7. **Feature Access Control**: Link approved registrations to feature flags
