"""
Tests for core security utilities.

Tests:
- Password hashing and verification
- JWT token creation and validation
- Token expiration
- WorkOS integration (mocked)
- Edge cases and security scenarios
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import jwt as pyjwt

from core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_jwt_token,
    create_token_pair,
    generate_session_token,
    generate_api_key,
    hash_api_key,
    WorkOSService,
)
from core.config import settings


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format
    
    def test_hash_password_different_each_time(self):
        """Test that hashing same password produces different hashes."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2  # Different salts
    
    def test_verify_password_success(self):
        """Test successful password verification."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test failed password verification."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword123!", hashed) is False
    
    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        hashed = hash_password("SecurePassword123!")
        
        assert verify_password("", hashed) is False
    
    def test_hash_empty_password(self):
        """Test hashing empty password."""
        # Should still work (but validation should prevent this)
        hashed = hash_password("")
        assert hashed is not None
        assert verify_password("", hashed) is True


class TestJWTTokens:
    """Test JWT token creation and validation."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify payload
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
        assert payload["username"] == "testuser"
        assert payload["user_type"] == "candidate"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = create_refresh_token(
            user_id=1,
            secret_key=settings.JWT_SECRET,
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify payload
        payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["user_id"] == 1
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_verify_jwt_token_success(self):
        """Test successful token verification."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        payload = verify_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
        
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
    
    def test_verify_jwt_token_expired(self):
        """Test verification of expired token."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        
        with pytest.raises(pyjwt.ExpiredSignatureError):
            verify_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
    
    def test_verify_jwt_token_invalid(self):
        """Test verification of invalid token."""
        with pytest.raises(pyjwt.InvalidTokenError):
            verify_jwt_token("invalid.token.here", settings.JWT_SECRET, settings.JWT_ALGORITHM)
    
    def test_verify_jwt_token_wrong_secret(self):
        """Test verification with wrong secret."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        with pytest.raises(pyjwt.InvalidTokenError):
            verify_jwt_token(token, "wrong_secret_key", settings.JWT_ALGORITHM)
    
    def test_create_token_pair(self):
        """Test creating access + refresh token pair."""
        tokens = create_token_pair(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        assert tokens is not None
        assert isinstance(tokens, dict)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert tokens["token_type"] == "Bearer"
        
        # Verify both tokens
        access_payload = pyjwt.decode(tokens["access_token"], settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        refresh_payload = pyjwt.decode(tokens["refresh_token"], settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_payload["user_id"] == refresh_payload["user_id"]
    
    def test_token_expiration_times(self):
        """Test that tokens have correct expiration times."""
        now = datetime.now(timezone.utc)
        
        access_token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        refresh_token = create_refresh_token(
            user_id=1,
            secret_key=settings.JWT_SECRET,
        )
        
        access_payload = pyjwt.decode(access_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        refresh_payload = pyjwt.decode(refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        access_exp = datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)
        refresh_exp = datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        
        # Access token should expire in ~1 hour
        access_delta = access_exp - now
        assert 55 * 60 <= access_delta.total_seconds() <= 65 * 60  # 55-65 minutes
        
        # Refresh token should expire in ~30 days
        refresh_delta = refresh_exp - now
        assert 29 * 24 * 3600 <= refresh_delta.total_seconds() <= 31 * 24 * 3600  # 29-31 days
    
    def test_token_jti_unique(self):
        """Test that each token has a unique JTI."""
        token1 = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        token2 = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        payload1 = pyjwt.decode(token1, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        payload2 = pyjwt.decode(token2, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        
        assert payload1["jti"] != payload2["jti"]


class TestSessionAndAPIKeys:
    """Test session token and API key generation."""
    
    def test_generate_session_token(self):
        """Test session token generation."""
        token = generate_session_token()
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) >= 32  # Should be sufficiently long
    
    def test_generate_session_token_unique(self):
        """Test that session tokens are unique."""
        token1 = generate_session_token()
        token2 = generate_session_token()
        
        assert token1 != token2
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()
        
        assert api_key is not None
        assert isinstance(api_key, str)
        assert len(api_key) >= 32
    
    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != api_key
        assert hashed.startswith("$2b$")  # bcrypt format
    
    def test_verify_api_key(self):
        """Test API key verification."""
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)
        
        # Use password verification for API keys
        assert verify_password(api_key, hashed) is True


class TestWorkOSService:
    """Test WorkOS integration."""
    
    @pytest.fixture
    def workos_service(self):
        """Create WorkOS service instance."""
        return WorkOSService(
            api_key="test_api_key",
            client_id="test_client_id",
            redirect_uri="http://localhost:8000/callback",
        )
    
    def test_initialization(self, workos_service):
        """Test WorkOS service initialization."""
        assert workos_service is not None
        assert workos_service.client_id == "test_client_id"
        assert workos_service.redirect_uri == "http://localhost:8000/callback"
    
    def test_get_authorization_url(self, workos_service):
        """Test getting WorkOS authorization URL."""
        with patch.object(workos_service.client.sso, 'get_authorization_url') as mock_get_url:
            mock_get_url.return_value = "https://workos.com/sso/authorize?..."
            
            url = workos_service.get_authorization_url(
                organization_id="org_123",
                state="random_state",
            )
            
            assert url is not None
            assert isinstance(url, str)
            assert "workos.com" in url
            mock_get_url.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_profile_and_token(self, workos_service):
        """Test getting user profile from WorkOS."""
        with patch.object(workos_service.client.sso, 'get_profile_and_token') as mock_get_profile:
            # Mock the profile object returned by WorkOS
            mock_profile = MagicMock(
                id="user_123",
                email="sso@example.com",
                first_name="SSO",
                last_name="User",
                connection_id="conn_123",
                organization_id="org_123",
                connection_type="GoogleOAuth",
                access_token="access_token_123",
                raw_attributes={"role": "admin"},
            )
            mock_get_profile.return_value = mock_profile
            
            result = await workos_service.get_profile_and_token(code="auth_code_123")
            
            assert result is not None
            assert result["workos_user_id"] == "user_123"
            assert result["email"] == "sso@example.com"
            assert result["first_name"] == "SSO"
            assert result["last_name"] == "User"
            assert result["connection_id"] == "conn_123"
            mock_get_profile.assert_called_once_with("auth_code_123")
    
    @pytest.mark.asyncio
    async def test_get_organization(self, workos_service):
        """Test getting organization from WorkOS."""
        with patch.object(workos_service.client.organizations, 'get_organization') as mock_get_org:
            # Mock the organization object returned by WorkOS
            mock_org = MagicMock()
            mock_org.id = "org_123"
            mock_org.name = "Acme Corp"
            mock_org.domains = ["acme.com"]
            mock_org.object = "organization"
            mock_org.created_at = "2024-01-01T00:00:00Z"
            mock_org.updated_at = "2024-01-01T00:00:00Z"
            mock_get_org.return_value = mock_org
            
            result = await workos_service.get_organization(organization_id="org_123")
            
            assert result is not None
            assert result["id"] == "org_123"
            assert result["name"] == "Acme Corp"
            assert result["domains"] == ["acme.com"]
            mock_get_org.assert_called_once_with("org_123")
    
    @pytest.mark.asyncio
    async def test_create_organization(self, workos_service):
        """Test creating organization in WorkOS."""
        with patch.object(workos_service.client.organizations, 'create_organization') as mock_create_org:
            # Mock the organization object returned by WorkOS
            mock_org = MagicMock()
            mock_org.id = "org_new_123"
            mock_org.name = "New Corp"
            mock_org.domains = ["newcorp.com"]
            mock_org.object = "organization"
            mock_org.created_at = "2024-01-01T00:00:00Z"
            mock_org.updated_at = "2024-01-01T00:00:00Z"
            mock_create_org.return_value = mock_org
            
            result = await workos_service.create_organization(
                name="New Corp",
                domains=["newcorp.com"],
            )
            
            assert result is not None
            assert result["id"] == "org_new_123"
            assert result["name"] == "New Corp"
            assert result["domains"] == ["newcorp.com"]
            mock_create_org.assert_called_once()


class TestSecurityEdgeCases:
    """Test security edge cases and attack vectors."""
    
    def test_jwt_algorithm_confusion(self):
        """Test that algorithm confusion attack is prevented."""
        # Create token with HS256
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        # Try to verify with different algorithm should fail
        with pytest.raises(pyjwt.InvalidTokenError):
            pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS512"])
    
    def test_jwt_none_algorithm(self):
        """Test that 'none' algorithm is rejected."""
        # Create token with 'none' algorithm
        payload = {
            "user_id": 1,
            "email": "test@example.com",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        token = pyjwt.encode(payload, "", algorithm="none")
        
        # Should fail verification
        with pytest.raises(pyjwt.InvalidTokenError):
            verify_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
    
    def test_timing_attack_password_verification(self):
        """Test that password verification is resistant to timing attacks."""
        import time
        
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        # Verify correct password
        start = time.time()
        verify_password(password, hashed)
        correct_time = time.time() - start
        
        # Verify incorrect password
        start = time.time()
        verify_password("WrongPassword123!", hashed)
        incorrect_time = time.time() - start
        
        # Times should be similar (bcrypt handles this internally)
        # Note: This is a basic check, proper timing attack tests require statistical analysis
        assert abs(correct_time - incorrect_time) < 0.1  # Within 100ms
    
    def test_jwt_token_tampering(self):
        """Test that tampering with JWT is detected."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        # Tamper with token (change one character)
        tampered_token = token[:-1] + ("X" if token[-1] != "X" else "Y")
        
        # Should fail verification
        with pytest.raises(pyjwt.InvalidTokenError):
            verify_jwt_token(tampered_token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
    
    def test_password_hash_sql_injection(self):
        """Test that password hashing handles SQL injection attempts."""
        malicious_password = "'; DROP TABLE users; --"
        
        # Should hash safely
        hashed = hash_password(malicious_password)
        assert hashed is not None
        
        # Should verify safely
        assert verify_password(malicious_password, hashed) is True
    
    def test_jwt_payload_injection(self):
        """Test that additional JWT claims don't break verification."""
        token = create_access_token(
            user_id=1,
            email="test@example.com",
            username="testuser",
            user_type="candidate",
            secret_key=settings.JWT_SECRET,
        )
        
        payload = verify_jwt_token(token, settings.JWT_SECRET, settings.JWT_ALGORITHM)
        
        # Ensure expected claims are present
        assert "user_id" in payload
        assert "email" in payload
        assert "type" in payload
        
        # Ensure no malicious claims
        assert "admin" not in payload
        assert "is_superuser" not in payload
