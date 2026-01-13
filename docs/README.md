# Documentation

## 🔐 Authentication & Authorization

**[Complete Guide: AUTH.md](AUTH.md)**

Everything you need to know about the authentication and authorization system:

- **Quick Start** - Get up and running in 5 minutes
- **Authentication** - JWT tokens, WorkOS SSO, email verification
- **Authorization** - Roles, permissions, multi-tenant security
- **API Reference** - All endpoints with examples
- **Usage Examples** - Code samples for common scenarios
- **Testing** - Running and writing tests
- **Security** - Best practices and compliance (GDPR, SOC2)
- **Configuration** - Environment variables and customization
- **Troubleshooting** - Common issues and solutions

### Quick Start

```bash
# 1. Run setup script
./setup_auth.sh

# 2. Update .env with credentials
# Edit .env and add WorkOS API key

# 3. Start application
uv run uvicorn api.main:app --reload

# 4. Test endpoints
open http://localhost:8000/docs
```

---

## 📚 Other Documentation

- **[Architecture](ARCHITECTURE.md)** - System design and architecture
- **[Database Schema](database.md)** - Database models and relationships
- **[Folder Structure](FOLDER_STRUCTURE.md)** - Project organization
- **[Quick Start](QUICKSTART.md)** - Getting started guide
- **[Migration Guide](MIGRATION_GUIDE.md)** - Upgrading and migrations
- **[Docker Setup](DOCKER.md)** - Containerization guide

---

## 🚀 Features

### Authentication ✅
- JWT-based authentication (access + refresh tokens)
- WorkOS SSO integration (Okta, Azure AD, Google Workspace)
- Email verification and password reset
- Session management with security tracking

### Authorization ✅
- 8 organization roles with hierarchical permissions
- 30+ granular permissions across all resource types
- Contextual permissions (hiring manager for specific jobs)
- Multi-tenant organization isolation

### Security ✅
- Bcrypt password hashing (12 rounds)
- JWT with HS256 algorithm
- Short-lived tokens (1 hour access, 30 day refresh)
- CSRF protection, SQL injection prevention
- GDPR and SOC2 compliant

---

## 📖 Need Help?

1. Check [AUTH.md](AUTH.md) for comprehensive documentation
2. Review test files in `tests/` for usage examples
3. Run `./setup_auth.sh` for automated setup
4. See [Troubleshooting](AUTH.md#troubleshooting) section

---

**Status**: ✅ Production Ready (after configuration)

**Version**: 1.0.0

**Last Updated**: 2024-01-12
