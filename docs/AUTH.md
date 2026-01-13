# 🔐 Authentication & Authorization

Complete authentication and authorization system for the ATS platform with JWT, WorkOS SSO, RBAC, and multi-tenant security.

---

## 🚀 Quick Start

```bash
# 1. Run setup script
./setup_auth.sh

# 2. Update .env with WorkOS credentials
# Edit .env file and add your WorkOS API key and client ID

# 3. Start the application
uv run uvicorn api.main:app --reload

# 4. Access API documentation
open http://localhost:8000/docs
```

### Features at a Glance

**Authentication** ✅
- JWT-based (access + refresh tokens)
- Email/password login
- WorkOS SSO (Okta, Azure AD, Google Workspace)
- Email verification & password reset
- Session management with security tracking

**Authorization** ✅
- 8 organization roles (OWNER → VIEWER)
- 30+ granular permissions
- Contextual permissions (hiring manager)
- Multi-tenant isolation
- Secure by default

**Security & Compliance** ✅
- Bcrypt password hashing (12 rounds)
- Short-lived tokens (1 hour access, 30 day refresh)
- GDPR compliant (data minimization, user rights)
- SOC2 compliant (audit logging, access control)

---

## 📋 Table of Contents

1. [Quick Start](#-quick-start)
2. [Authentication](#authentication)
3. [Authorization](#authorization)
4. [WorkOS SSO](#workos-sso)
5. [API Reference](#api-reference)
6. [Usage Examples](#usage-examples)
7. [Testing](#testing)
8. [Security Best Practices](#security-best-practices)
9. [GDPR & SOC2 Compliance](#gdpr--soc2-compliance)
10. [Configuration](#configuration)
11. [Troubleshooting](#troubleshooting)

---

## Authentication

### Overview

The system uses JWT (JSON Web Tokens) for stateless authentication with session tracking for security and audit purposes.

### Token Types

#### Access Token
- **Purpose**: Authenticate API requests
- **Expiry**: 1 hour (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Claims**:
  ```json
  {
    "user_id": 1,
    "email": "user@example.com",
    "username": "username",
    "user_type": "candidate",
    "type": "access",
    "exp": 1234567890,
    "iat": 1234567890,
    "jti": "unique-session-token"
  }
  ```

#### Refresh Token
- **Purpose**: Obtain new access tokens
- **Expiry**: 30 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Claims**:
  ```json
  {
    "user_id": 1,
    "type": "refresh",
    "exp": 1234567890,
    "iat": 1234567890,
    "jti": "unique-session-token"
  }
  ```

### Authentication Flow

#### 1. Signup

```bash
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "username",
  "first_name": "John",
  "last_name": "Doe",
  "organization_name": "Acme Corp"  // Optional - creates new org
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "username",
    "user_type": "candidate",
    "email_verified": false
  }
}
```

#### 2. Login

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "remember_me": false  // Optional - extends refresh token expiry
}
```

**Response:** Same as signup

#### 3. Using Access Token

```bash
GET /api/v1/protected-resource
Authorization: Bearer eyJ...
```

#### 4. Refreshing Token

```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

**Response:** New token pair

#### 5. Logout

```bash
POST /api/v1/auth/logout
Authorization: Bearer eyJ...
```

Invalidates the current session.

### Password Requirements

Passwords must meet the following criteria:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- Special characters recommended but not required

### Email Verification

1. User signs up → receives verification email
2. User clicks verification link with token
3. POST to `/api/v1/auth/verify-email` with token
4. Email marked as verified

### Password Reset

1. User requests reset: `POST /api/v1/auth/forgot-password`
2. User receives reset email with token
3. User submits new password: `POST /api/v1/auth/reset-password`
4. Password updated, all sessions invalidated

---

## Authorization

### Role-Based Access Control (RBAC)

The system implements RBAC with organization-level roles:

| Role | Description | Use Case |
|------|-------------|----------|
| **OWNER** | Full organization control | Organization founder |
| **ADMIN** | Full administrative access | IT administrators |
| **RECRUITER** | Manage jobs and applications | HR team members |
| **HIRING_MANAGER** | Manage specific jobs | Department heads |
| **INTERVIEWER** | View and review candidates | Technical interviewers |
| **COORDINATOR** | Manage scheduling | HR coordinators |
| **MEMBER** | Basic member access | Regular employees |
| **VIEWER** | Read-only access | Auditors, observers |

### Permission System

30+ granular permissions organized by resource:

#### Organization Permissions
- `ORG_VIEW` - View organization details
- `ORG_EDIT` - Edit organization settings
- `ORG_DELETE` - Delete organization
- `ORG_ADMIN` - Full organization control

#### Job Permissions
- `JOB_CREATE` - Create new job postings
- `JOB_VIEW` - View job details
- `JOB_EDIT` - Edit job postings
- `JOB_DELETE` - Delete job postings
- `JOB_PUBLISH` - Publish/unpublish jobs

#### Application Permissions
- `APPLICATION_VIEW` - View applications
- `APPLICATION_REVIEW` - Review and score applications
- `APPLICATION_REJECT` - Reject applications
- `APPLICATION_ADVANCE` - Move to next stage

#### Candidate Permissions
- `CANDIDATE_VIEW` - View candidate profiles
- `CANDIDATE_CREATE` - Create candidate records
- `CANDIDATE_EDIT` - Edit candidate information
- `CANDIDATE_DELETE` - Delete candidates

#### Offer Permissions
- `OFFER_CREATE` - Create job offers
- `OFFER_VIEW` - View offers
- `OFFER_APPROVE` - Approve offers
- `OFFER_SEND` - Send offers to candidates

#### User Management
- `USER_INVITE` - Invite users to organization
- `USER_MANAGE` - Manage user roles and permissions

#### Analytics & Settings
- `ANALYTICS_VIEW` - View reports and analytics
- `SETTINGS_VIEW` - View settings
- `SETTINGS_EDIT` - Edit settings

### Role-Permission Mapping

```python
# Example: RECRUITER permissions
RECRUITER_PERMISSIONS = {
    Permission.JOB_CREATE,
    Permission.JOB_VIEW,
    Permission.JOB_EDIT,
    Permission.JOB_PUBLISH,
    Permission.APPLICATION_VIEW,
    Permission.APPLICATION_REVIEW,
    Permission.APPLICATION_REJECT,
    Permission.APPLICATION_ADVANCE,
    Permission.CANDIDATE_VIEW,
    Permission.CANDIDATE_CREATE,
    Permission.CANDIDATE_EDIT,
    # ... more permissions
}
```

### Contextual Permissions

Some permissions are context-dependent:

#### Hiring Manager Access

Hiring managers have full access to **only** the jobs they're assigned to:

```python
# Check if user is hiring manager for specific job
if job.hiring_manager_id == current_user.id:
    # Grant access to review applications
    allow_access(Permission.APPLICATION_REVIEW)
```

#### Department-Level Access (Future)

```python
# Check department-level access
if user.department_id == job.department_id:
    # Grant departmental access
```

### Checking Permissions

#### In Endpoints (Dependency Injection)

```python
from fastapi import Depends
from core.middleware.authorization import require_permission, Permission

@router.post("/jobs")
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    # Require JOB_CREATE permission
    _: None = Depends(require_permission(Permission.JOB_CREATE, organization_id_param="organization_id"))
):
    # User has permission, create job
    pass
```

#### Programmatic Check

```python
from core.middleware.authorization import check_permission, Permission

# Check if user has permission
has_permission = await check_permission(
    db=db,
    user_id=user.id,
    organization_id=org.id,
    permission=Permission.JOB_CREATE
)

if not has_permission:
    raise HTTPException(status_code=403, detail="Insufficient permissions")
```

#### Job-Specific Check

```python
from core.middleware.authorization import check_job_specific_permission

# Check hiring manager permission for specific job
await check_job_specific_permission(
    db=db,
    user_id=user.id,
    job_id=job.id,
    permission=Permission.APPLICATION_REVIEW
)
```

---

## WorkOS SSO

### Setup

1. **Create WorkOS Account**: Sign up at [workos.com](https://workos.com)

2. **Configure Environment Variables**:
```bash
WORKOS_API_KEY=sk_test_...
WORKOS_CLIENT_ID=client_...
WORKOS_REDIRECT_URI=http://localhost:8000/api/v1/auth/sso/callback
```

3. **Configure SSO Connection** in WorkOS dashboard

### SSO Flow

#### 1. Initiate SSO

```bash
GET /api/v1/auth/sso/workos?organization_id=org_123
```

Redirects to WorkOS authorization page.

#### 2. User Authenticates

User logs in via their identity provider (Okta, Azure AD, Google Workspace, etc.)

#### 3. Callback

WorkOS redirects to callback URL with authorization code:

```bash
GET /api/v1/auth/sso/callback?code=auth_code_123&state=random_state
```

#### 4. Token Exchange

System exchanges code for user profile and creates/updates user account.

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "user@acme.com",
    "workos_user_id": "workos_user_123",
    "email_verified": true  // Verified via SSO
  }
}
```

### Organization Sync

WorkOS organizations are automatically synced:

```python
# User belongs to WorkOS organization
workos_org = workos_service.get_organization(organization_id)

# Create or update local organization
organization = Organization(
    workos_org_id=workos_org["workos_org_id"],
    name=workos_org["name"],
    domains=workos_org["domains"]
)
```

---

## Multi-Tenant Security

### Organization Isolation

Every resource belongs to an organization:

```python
# Jobs are scoped to organizations
job = Job(
    title="Senior Developer",
    organization_id=1  # Belongs to org 1
)

# Users can only access resources in their organizations
user_orgs = user.organizations  # List of organizations user belongs to

# Check access
if job.organization_id not in [org.id for org in user_orgs]:
    raise HTTPException(status_code=403, detail="Access denied")
```

### User-Organization Membership

```python
# Many-to-many relationship
organization_users = OrganizationUsers(
    user_id=1,
    organization_id=1,
    role=OrganizationRoles.RECRUITER,
    joined_at=datetime.now()
)
```

### Access Control Flow

```
1. Extract JWT from Authorization header
   ↓
2. Validate token signature and expiration
   ↓
3. Load user from database
   ↓
4. Check user is active and email verified
   ↓
5. Load user's organization memberships
   ↓
6. Check resource belongs to user's organization
   ↓
7. Check user has required permission in organization
   ↓
8. Allow access
```

---

## Security Best Practices

### Password Security

- **Hashing**: bcrypt with 12 rounds
- **Storage**: Only hash stored, never plaintext
- **Validation**: Strong password requirements enforced

```python
from core.security import hash_password, verify_password

# Hash password before storing
password_hash = hash_password("user_password")

# Verify during login
is_valid = verify_password("user_input", password_hash)
```

### JWT Security

- **Algorithm**: HS256 (configurable)
- **Secret**: Strong random secret (min 32 bytes)
- **Expiration**: Short-lived access tokens (1 hour)
- **Validation**: Signature, expiration, claims validated

### Session Management

- **Tracking**: IP address and user-agent logged
- **Expiration**: Configurable session timeout
- **Revocation**: Sessions can be invalidated (logout)
- **Monitoring**: Unusual session activity detected

### Rate Limiting

Protected endpoints have rate limits:

```python
# Login endpoint: 5 requests per minute
"/api/v1/auth/login": {"limit": 5, "period": 60}

# Signup endpoint: 3 requests per hour
"/api/v1/auth/signup": {"limit": 3, "period": 3600}
```

### CSRF Protection

- **State Parameter**: Random state in SSO flow
- **Token Binding**: JTI claim links token to session
- **SameSite Cookies**: If using cookie auth

### Input Validation

- **Email**: RFC 5322 compliant
- **Password**: Complexity requirements
- **Username**: Alphanumeric + underscore only
- **SQL Injection**: Parameterized queries via SQLAlchemy

---

## GDPR & SOC2 Compliance

### GDPR Compliance

#### Data Minimization
- Only necessary user data collected
- Optional fields clearly marked
- No excessive data retention

#### User Rights
- **Access**: `GET /api/v1/users/me` - view own data
- **Rectification**: `PATCH /api/v1/users/me` - update data
- **Erasure**: `DELETE /api/v1/users/me` - delete account
- **Portability**: Export user data (future)

#### Consent & Purpose
- Clear privacy policy during signup
- Purpose of data collection explained
- Consent logged with timestamp

#### Security
- Encryption at rest and in transit
- Access controls and audit logs
- Regular security assessments

### SOC2 Compliance

#### Access Control
- Role-based access control (RBAC)
- Principle of least privilege
- Regular permission audits

#### Audit Logging
All authentication events logged:
- Login attempts (success/failure)
- Logout events
- Password changes
- Permission changes
- Failed authorization attempts

```python
# Example audit log entry
{
    "timestamp": "2024-01-12T10:30:00Z",
    "event_type": "auth.login.success",
    "user_id": 1,
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "organization_id": 1
}
```

#### Session Management
- Sessions tracked with expiration
- IP and user-agent monitoring
- Anomaly detection (future)

#### Change Management
- All schema changes versioned (Alembic)
- Code review required for auth changes
- Automated security testing

---

## API Reference

### Authentication Endpoints

#### POST /api/v1/auth/signup
Create new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "username": "username",
  "first_name": "John",
  "last_name": "Doe",
  "organization_name": "Acme Corp"  // Optional
}
```

**Response:** 201 Created
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": { ... }
}
```

**Errors:**
- `409 Conflict` - Email or username already exists
- `422 Validation Error` - Invalid input

#### POST /api/v1/auth/login
Authenticate user.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "remember_me": false
}
```

**Response:** 200 OK (same as signup)

**Errors:**
- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Email not verified or account inactive

#### POST /api/v1/auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:** 200 OK
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Errors:**
- `401 Unauthorized` - Invalid or expired refresh token

#### POST /api/v1/auth/logout
Invalidate current session.

**Headers:**
```
Authorization: Bearer eyJ...
```

**Response:** 200 OK
```json
{
  "message": "Successfully logged out"
}
```

#### GET /api/v1/auth/me
Get current user information.

**Headers:**
```
Authorization: Bearer eyJ...
```

**Response:** 200 OK
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "username",
  "first_name": "John",
  "last_name": "Doe",
  "user_type": "candidate",
  "email_verified": true,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### SSO Endpoints

#### GET /api/v1/auth/sso/workos
Initiate WorkOS SSO flow.

**Query Parameters:**
- `organization_id` (optional): WorkOS organization ID

**Response:** 200 OK or 307 Redirect
```json
{
  "authorization_url": "https://workos.com/sso/authorize?..."
}
```

#### GET /api/v1/auth/sso/callback
Handle WorkOS SSO callback.

**Query Parameters:**
- `code`: Authorization code from WorkOS
- `state`: CSRF protection token

**Response:** 200 OK
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": { ... }
}
```

---

## Testing

### Running Tests

```bash
# Run all auth tests
pytest tests/unit/api/test_auth_endpoints.py -v

# Run specific test class
pytest tests/unit/api/test_auth_endpoints.py::TestSignup -v

# Run with coverage
pytest tests/ --cov=core.security --cov=core.middleware --cov=api.routes.v1.auth

# Run integration tests
pytest tests/integration/test_auth_flow.py -v
```

### Test Coverage

Comprehensive tests cover:
- ✅ Signup flow (valid/invalid inputs)
- ✅ Login flow (success/failure scenarios)
- ✅ Token refresh
- ✅ Logout and session invalidation
- ✅ Password reset flow
- ✅ Email verification
- ✅ WorkOS SSO integration
- ✅ Permission checking
- ✅ Multi-tenant isolation
- ✅ Security edge cases
- ✅ GDPR compliance
- ✅ SOC2 audit requirements

### Example Tests

```python
# Test successful signup
def test_signup_success(client, test_user_data):
    response = client.post("/api/v1/auth/signup", json=test_user_data)
    
    assert response.status_code == 201
    assert "access_token" in response.json()
    assert "user" in response.json()

# Test permission check
@pytest.mark.asyncio
async def test_recruiter_can_create_jobs():
    has_permission = await check_permission(
        db=db,
        user_id=recruiter_user.id,
        organization_id=org.id,
        permission=Permission.JOB_CREATE
    )
    
    assert has_permission is True
```

---

## Troubleshooting

### Common Issues

#### "Invalid or expired token"
- Check token expiration (`exp` claim)
- Verify JWT_SECRET matches between token creation and validation
- Ensure token type is correct (access vs refresh)

#### "Email not verified"
- User must verify email before login
- Check `email_verified` field in user table
- Resend verification email if needed

#### "Insufficient permissions"
- Check user's role in organization (`OrganizationUsers` table)
- Verify role has required permission (`ROLE_PERMISSIONS` mapping)
- Check if resource belongs to user's organization

#### "Session invalid"
- Session may be expired or revoked
- Check `UserSession` table for active sessions
- User may need to re-login

### Debug Mode

Enable debug logging:

```python
# core/config.py
DEBUG = True

# Logs will show:
# - JWT validation details
# - Permission checks
# - Database queries
# - Session management
```

---

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET=your-secret-key-min-32-bytes
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# WorkOS Configuration
WORKOS_API_KEY=sk_test_...
WORKOS_CLIENT_ID=client_...
WORKOS_REDIRECT_URI=http://localhost:8000/api/v1/auth/sso/callback

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db

# Security
BCRYPT_ROUNDS=12
SESSION_TIMEOUT_DAYS=30
```

### Customization

#### Custom Token Expiration

```python
# core/config.py
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes instead of 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 90  # 90 days instead of 30
```

#### Custom Permissions

```python
# core/middleware/authorization.py

# Add new permission
class Permission(str, Enum):
    # ... existing permissions
    CUSTOM_PERMISSION = "custom_permission"

# Update role mapping
ROLE_PERMISSIONS = {
    OrganizationRoles.CUSTOM_ROLE: {
        Permission.CUSTOM_PERMISSION,
        # ... other permissions
    }
}
```

---

## Changelog

### Version 1.0.0 (2024-01-12)
- ✅ JWT authentication with access + refresh tokens
- ✅ WorkOS SSO integration
- ✅ Role-based access control (8 roles)
- ✅ 30+ granular permissions
- ✅ Contextual permissions (hiring manager)
- ✅ Multi-tenant organization isolation
- ✅ Password reset flow
- ✅ Email verification
- ✅ Session management
- ✅ GDPR compliance features
- ✅ SOC2 audit logging
- ✅ Comprehensive test suite

---

## Support

For issues or questions:
- Check [troubleshooting](#troubleshooting) section
- Review test files for usage examples
- Open an issue on GitHub
- Contact security team for security concerns
