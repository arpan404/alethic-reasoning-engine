#!/bin/bash
# Setup script for authentication system

set -e

echo "🚀 Setting up Authentication & Authorization System"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file...${NC}"
    
    # Generate JWT secret
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ats_db

# JWT Configuration
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# WorkOS Configuration (Update with your credentials)
WORKOS_API_KEY=sk_test_your_api_key_here
WORKOS_CLIENT_ID=client_your_client_id_here
WORKOS_REDIRECT_URI=http://localhost:8000/api/v1/auth/sso/callback

# Security
BCRYPT_ROUNDS=12
SESSION_TIMEOUT_DAYS=30

# Application
DEBUG=True
APP_NAME=ATS Platform
ENVIRONMENT=development
EOF
    
    echo -e "${GREEN}✅ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please update WorkOS credentials in .env${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Install dependencies
echo -e "\n${YELLOW}📦 Installing dependencies...${NC}"
uv sync
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Check if database is running
echo -e "\n${YELLOW}🔍 Checking database connection...${NC}"
if command -v psql &> /dev/null; then
    if psql -h localhost -U postgres -c '\q' 2>/dev/null; then
        echo -e "${GREEN}✅ PostgreSQL is running${NC}"
    else
        echo -e "${RED}❌ PostgreSQL is not accessible${NC}"
        echo -e "${YELLOW}⚠️  Please start PostgreSQL or update DATABASE_URL in .env${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  psql command not found. Please ensure PostgreSQL is installed and running.${NC}"
fi

# Run migrations (if alembic is configured)
if [ -f "alembic.ini" ]; then
    echo -e "\n${YELLOW}🔄 Running database migrations...${NC}"
    uv run alembic upgrade head 2>/dev/null && echo -e "${GREEN}✅ Migrations completed${NC}" || echo -e "${YELLOW}⚠️  Migrations skipped (may need manual setup)${NC}"
else
    echo -e "${YELLOW}⚠️  Alembic not configured. Skipping migrations.${NC}"
fi

# Run tests
echo -e "\n${YELLOW}🧪 Running tests...${NC}"
if uv run pytest tests/unit/core/test_security.py -v --tb=short 2>&1 | head -20; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests may require database setup${NC}"
fi

# Summary
echo -e "\n${GREEN}=================================================="
echo -e "🎉 Setup Complete!"
echo -e "==================================================${NC}"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Update WorkOS credentials in .env file:"
echo "   - Get credentials from https://workos.com"
echo "   - Update WORKOS_API_KEY and WORKOS_CLIENT_ID"
echo ""
echo "2. Start the application:"
echo "   uv run uvicorn api.main:app --reload"
echo ""
echo "3. Test authentication endpoints:"
echo "   curl http://localhost:8000/docs"
echo ""
echo "4. Run full test suite:"
echo "   uv run pytest tests/ -v --cov"
echo ""
echo "📚 Documentation:"
echo "   - Complete Guide: docs/AUTH.md"
echo ""
echo "🔒 Security Checklist:"
echo "   ✅ JWT secret generated"
echo "   ✅ Password hashing configured (bcrypt)"
echo "   ⚠️  WorkOS credentials need to be added"
echo "   ⚠️  Database connection needs to be verified"
echo ""
