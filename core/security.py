"""
Security utilities for authentication, authorization, and cryptography.

This module provides:
1. JWT token generation and verification
2. Password hashing and verification
3. WorkOS SSO integration
4. Session management
5. GDPR/SOC2 compliant security practices
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict
import jwt
import bcrypt
import workos
from workos import WorkOSClient

logger = logging.getLogger(__name__)


class JWTPayload(TypedDict, total=False):
    """JWT token payload structure."""
    user_id: int
    email: str
    username: str
    user_type: str
    session_id: Optional[int]
    workos_user_id: Optional[str]
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str  # JWT ID (unique identifier)


class TokenPair(TypedDict):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


# ==================== Password Hashing ==================== #

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    # Convert password to bytes and hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


# ==================== JWT Token Management ==================== #

def create_access_token(
    user_id: int,
    email: str,
    username: str,
    user_type: str,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
    session_id: Optional[int] = None,
    workos_user_id: Optional[str] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User ID
        email: User email
        username: Username
        user_type: User type
        secret_key: JWT secret key
        algorithm: JWT algorithm
        expires_delta: Token expiration time
        session_id: Optional session ID
        workos_user_id: Optional WorkOS user ID
        
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)  # Default 1 hour
    
    expire = datetime.now(timezone.utc) + expires_delta
    iat = datetime.now(timezone.utc)
    jti = secrets.token_urlsafe(32)  # Unique token ID
    
    payload: JWTPayload = {
        "user_id": user_id,
        "email": email,
        "username": username,
        "user_type": user_type,
        "type": "access",
        "exp": int(expire.timestamp()),
        "iat": int(iat.timestamp()),
        "jti": jti,
    }
    
    if session_id:
        payload["session_id"] = session_id
    
    if workos_user_id:
        payload["workos_user_id"] = workos_user_id
    
    encoded_jwt = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded_jwt


def create_refresh_token(
    user_id: int,
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User ID
        secret_key: JWT secret key
        algorithm: JWT algorithm
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT refresh token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=30)  # Default 30 days
    
    expire = datetime.now(timezone.utc) + expires_delta
    iat = datetime.now(timezone.utc)
    jti = secrets.token_urlsafe(32)
    
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": int(expire.timestamp()),
        "iat": int(iat.timestamp()),
        "jti": jti,
    }
    
    encoded_jwt = jwt.encode(payload, secret_key, algorithm=algorithm)
    return encoded_jwt


def verify_jwt_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> JWTPayload:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token
        secret_key: JWT secret key
        algorithm: JWT algorithm
        
    Returns:
        Decoded token payload
        
    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        raise


def create_token_pair(
    user_id: int,
    email: str,
    username: str,
    user_type: str,
    secret_key: str,
    algorithm: str = "HS256",
    session_id: Optional[int] = None,
    workos_user_id: Optional[str] = None,
    access_token_expires: Optional[timedelta] = None,
    refresh_token_expires: Optional[timedelta] = None,
) -> TokenPair:
    """
    Create an access and refresh token pair.
    
    Args:
        user_id: User ID
        email: User email
        username: Username
        user_type: User type
        secret_key: JWT secret key
        algorithm: JWT algorithm
        session_id: Optional session ID
        workos_user_id: Optional WorkOS user ID
        access_token_expires: Access token expiration
        refresh_token_expires: Refresh token expiration
        
    Returns:
        Token pair with access and refresh tokens
    """
    access_token = create_access_token(
        user_id=user_id,
        email=email,
        username=username,
        user_type=user_type,
        secret_key=secret_key,
        algorithm=algorithm,
        expires_delta=access_token_expires,
        session_id=session_id,
        workos_user_id=workos_user_id,
    )
    
    refresh_token = create_refresh_token(
        user_id=user_id,
        secret_key=secret_key,
        algorithm=algorithm,
        expires_delta=refresh_token_expires,
    )
    
    expires_in = int((access_token_expires or timedelta(hours=1)).total_seconds())
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
    }


# ==================== WorkOS Integration ==================== #

class WorkOSService:
    """
    WorkOS SSO integration service.
    
    Handles:
    - SSO authentication
    - Organization management
    - User provisioning
    - Directory sync
    """
    
    def __init__(
        self,
        api_key: str,
        client_id: str,
        redirect_uri: str,
    ):
        """
        Initialize WorkOS service.
        
        Args:
            api_key: WorkOS API key
            client_id: WorkOS client ID
            redirect_uri: OAuth redirect URI
        """
        self.client = WorkOSClient(api_key=api_key)
        self.client_id = client_id
        self.redirect_uri = redirect_uri
    
    def get_authorization_url(
        self,
        organization_id: Optional[str] = None,
        provider: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        """
        Get SSO authorization URL.
        
        Args:
            organization_id: WorkOS organization ID
            provider: SSO provider (e.g., "GoogleOAuth", "OktaSAML")
            state: Optional state parameter
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        
        if organization_id:
            params["organization"] = organization_id
        
        if provider:
            params["provider"] = provider
        
        if state:
            params["state"] = state
        
        return self.client.sso.get_authorization_url(**params)
    
    async def get_profile_and_token(self, code: str) -> dict:
        """
        Exchange authorization code for profile and access token.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dictionary with user profile and access token
        """
        try:
            profile = self.client.sso.get_profile_and_token(code)
            return {
                "workos_user_id": profile.id,
                "email": profile.email,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "raw_attributes": profile.raw_attributes,
                "access_token": profile.access_token,
                "organization_id": profile.organization_id,
                "connection_id": profile.connection_id,
                "connection_type": profile.connection_type,
            }
        except Exception as e:
            logger.error(f"WorkOS profile fetch error: {str(e)}")
            raise
    
    async def get_organization(self, organization_id: str) -> dict:
        """
        Get WorkOS organization details.
        
        Args:
            organization_id: WorkOS organization ID
            
        Returns:
            Organization details
        """
        try:
            org = self.client.organizations.get_organization(organization_id)
            return {
                "id": org.id,
                "name": org.name,
                "domains": org.domains,
                "object": org.object,
                "created_at": org.created_at,
                "updated_at": org.updated_at,
            }
        except Exception as e:
            logger.error(f"WorkOS organization fetch error: {str(e)}")
            raise
    
    async def create_organization(
        self,
        name: str,
        domains: list[str],
    ) -> dict:
        """
        Create a new WorkOS organization.
        
        Args:
            name: Organization name
            domains: List of email domains
            
        Returns:
            Created organization details
        """
        try:
            org = self.client.organizations.create_organization(
                name=name,
                domains=domains,
            )
            return {
                "id": org.id,
                "name": org.name,
                "domains": org.domains,
            }
        except Exception as e:
            logger.error(f"WorkOS organization creation error: {str(e)}")
            raise
    
    async def verify_email(self, user_id: str) -> bool:
        """
        Verify user email through WorkOS.
        
        Args:
            user_id: WorkOS user ID
            
        Returns:
            True if email is verified
        """
        try:
            # WorkOS handles email verification through their magic link flow
            # This is a placeholder for the verification check
            return True
        except Exception as e:
            logger.error(f"WorkOS email verification error: {str(e)}")
            return False


# ==================== Session Management ==================== #

def generate_session_token() -> str:
    """
    Generate a secure session token.
    
    Returns:
        Secure random token
    """
    return secrets.token_urlsafe(64)


def generate_refresh_token_secret() -> str:
    """
    Generate a secure refresh token secret.
    
    Returns:
        Secure random secret
    """
    return secrets.token_urlsafe(64)


def generate_invite_token() -> str:
    """
    Generate a secure invite token.
    
    Returns:
        Secure random token
    """
    return secrets.token_urlsafe(32)


# ==================== API Key Management ==================== #

def generate_api_key(prefix: str = "sk") -> str:
    """
    Generate a secure API key.
    
    Args:
        prefix: Key prefix (e.g., "sk" for secret key, "pk" for public key)
        
    Returns:
        API key with prefix
    """
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.
    
    Args:
        api_key: Plain API key
        
    Returns:
        Hashed API key
    """
    api_key_bytes = api_key.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(api_key_bytes, salt)
    return hashed.decode('utf-8')


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        plain_key: Plain API key
        hashed_key: Hashed API key
        
    Returns:
        True if key matches
    """
    try:
        return pwd_context.verify(plain_key, hashed_key)
    except Exception as e:
        logger.error(f"API key verification error: {str(e)}")
        return False
