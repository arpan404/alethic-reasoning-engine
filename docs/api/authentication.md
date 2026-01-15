# Authentication

## Overview

Alethic uses JWT (JSON Web Tokens) for API authentication. Tokens are issued upon successful login and must be included in all API requests.

## Obtaining a Token

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@company.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLC...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLC...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the access token in all subsequent requests:

```http
GET /api/v1/candidates
Authorization: Bearer eyJ0eXAiOiJKV1QiLC...
```

## Token Refresh

Access tokens expire after 1 hour. Use the refresh token to obtain new access tokens:

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLC..."
}
```

## SSO (Single Sign-On)

Enterprise customers can use WorkOS SSO integration:

```http
GET /api/v1/auth/sso/authorize?organization=your-org
```

This redirects to your identity provider. After authentication, the callback provides tokens.

## Permissions

API access is controlled by role-based permissions:

| Role | Permissions |
|------|-------------|
| Admin | Full access |
| Recruiter | Candidates, Applications, Interviews |
| Hiring Manager | View candidates, Evaluations |
| Interviewer | Assigned interviews only |

## Security Best Practices

1. **Never expose tokens** in client-side code or logs
2. **Use HTTPS** for all API calls
3. **Rotate tokens** regularly
4. **Implement token refresh** before expiry
5. **Store tokens securely** (HttpOnly cookies or secure storage)
