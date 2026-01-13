"""
Authentication endpoints for user login, signup, and SSO.

Provides:
- Email/password login and signup
- WorkOS SSO integration
- Token refresh
- Logout
- Password reset
- Email verification
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, validator

from database.engine import get_db_session
from database.models.users import User, UserSession, UserType
from database.models.organizations import Organization, OrganizationUsers, OrganizationRoles
from core.security import (
    hash_password,
    verify_password,
    create_token_pair,
    verify_jwt_token,
    WorkOSService,
    generate_session_token,
    generate_invite_token,
)
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# ==================== Request/Response Models ==================== #

class SignupRequest(BaseModel):
    """User signup request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    organization_name: Optional[str] = Field(None, max_length=255)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class EmailVerificationRequest(BaseModel):
    """Email verification request."""
    token: str


class AuthResponse(BaseModel):
    """Authentication response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class UserResponse(BaseModel):
    """User information response."""
    id: int
    email: str
    username: str
    first_name: str
    last_name: str
    user_type: str
    email_verified: bool
    is_active: bool
    created_at: datetime


# ==================== Helper Functions ==================== #

async def create_user_session(
    db: AsyncSession,
    user: User,
    ip_address: Optional[str],
    user_agent: Optional[str],
    expires_delta: Optional[timedelta] = None,
) -> UserSession:
    """
    Create a new user session.
    
    Args:
        db: Database session
        user: User
        ip_address: Client IP address
        user_agent: Client user agent
        expires_delta: Session expiration time
        
    Returns:
        Created user session
    """
    if expires_delta is None:
        expires_delta = timedelta(days=30)
    
    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + expires_delta
    
    session = UserSession(
        user_id=user.id,
        session_token=session_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return session


def user_to_dict(user: User) -> dict:
    """Convert user model to dictionary."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "user_type": user.user_type.value,
        "email_verified": user.email_verified,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
    }


# ==================== Endpoints ==================== #

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    signup_data: SignupRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Register a new user account.
    
    Creates:
    - User account with hashed password
    - Default organization if organization_name provided
    - User session
    - JWT tokens
    
    Returns:
        Authentication response with tokens and user info
    """
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == signup_data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    # Check if username already exists
    result = await db.execute(
        select(User).where(User.username == signup_data.username)
    )
    existing_username = result.scalar_one_or_none()
    
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    
    # Hash password
    hashed_password = hash_password(signup_data.password)
    
    # Create user
    user = User(
        email=signup_data.email,
        username=signup_data.username,
        first_name=signup_data.first_name,
        last_name=signup_data.last_name,
        password_hash=hashed_password,
        user_type=UserType.ORG_ADMIN if signup_data.organization_name else UserType.CANDIDATE,
        is_active=True,
        email_verified=False,  # Require email verification
    )
    
    db.add(user)
    await db.flush()  # Get user.id
    
    # Create organization if provided
    organization = None
    if signup_data.organization_name:
        # Generate workspace slug from organization name
        workspace = signup_data.organization_name.lower().replace(' ', '-').replace('_', '-')
        # Add random suffix if needed for uniqueness
        import random
        workspace = f"{workspace}-{random.randint(1000, 9999)}"
        
        organization = Organization(
            name=signup_data.organization_name,
            workspace=workspace,
            owner=user.id,
            is_active=True,
        )
        db.add(organization)
        await db.flush()
        
        # Add user as organization owner
        org_membership = OrganizationUsers(
            organization_id=organization.id,
            user_id=user.id,
            role=OrganizationRoles.OWNER,
        )
        db.add(org_membership)
    
    await db.commit()
    await db.refresh(user)
    
    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    session = await create_user_session(
        db, user, ip_address, user_agent
    )
    
    # Generate tokens
    tokens = create_token_pair(
        user_id=user.id,
        email=user.email,
        username=user.username,
        user_type=user.user_type.value,
        secret_key=settings.JWT_SECRET,
        session_id=session.id,
    )
    
    logger.info(f"User {user.id} ({user.email}) registered successfully")
    
    return {
        **tokens,
        "user": user_to_dict(user),
    }


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Login with email and password.
    
    Validates:
    - User exists
    - Password is correct
    - User is active
    - Email is verified
    
    Returns:
        Authentication response with tokens and user info
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Use generic message to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Verify password
    if not user.password_hash or not verify_password(login_data.password, user.password_hash):
        logger.warning(f"Failed login attempt for {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )
    
    # Check if email is verified
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for verification link.",
        )
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    # Create session
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    expires_delta = timedelta(days=30) if login_data.remember_me else timedelta(days=7)
    session = await create_user_session(
        db, user, ip_address, user_agent, expires_delta
    )
    
    await db.commit()
    
    # Generate tokens
    access_expires = timedelta(hours=1)
    refresh_expires = expires_delta
    
    tokens = create_token_pair(
        user_id=user.id,
        email=user.email,
        username=user.username,
        user_type=user.user_type.value,
        secret_key=settings.JWT_SECRET,
        session_id=session.id,
        access_token_expires=access_expires,
        refresh_token_expires=refresh_expires,
    )
    
    logger.info(f"User {user.id} ({user.email}) logged in successfully")
    
    return {
        **tokens,
        "user": user_to_dict(user),
    }


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_data: Refresh token request
        
    Returns:
        New authentication response with fresh tokens
    """
    try:
        # Verify refresh token
        payload = verify_jwt_token(
            refresh_data.refresh_token,
            settings.JWT_SECRET,
        )
        
        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        # Load user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        # Generate new tokens
        tokens = create_token_pair(
            user_id=user.id,
            email=user.email,
            username=user.username,
            user_type=user.user_type.value,
            secret_key=settings.JWT_SECRET,
            workos_user_id=user.workos_user_id,
        )
        
        logger.info(f"User {user.id} refreshed access token")
        
        return {
            **tokens,
            "user": user_to_dict(user),
        }
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Logout user and revoke session.
    
    Requires:
        Valid JWT token in Authorization header
        
    Returns:
        Success message
    """
    # Get session from request scope (set by authentication middleware)
    session = request.scope.get("session")
    
    if session:
        # Revoke session
        session.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info(f"Session {session.id} revoked for user {session.user_id}")
    
    return {"message": "Logged out successfully"}


@router.get("/sso/workos")
async def workos_sso_redirect(
    organization_id: Optional[str] = None,
    provider: Optional[str] = None,
):
    """
    Redirect to WorkOS SSO authentication.
    
    Args:
        organization_id: WorkOS organization ID (optional)
        provider: SSO provider (optional, e.g., "GoogleOAuth", "OktaSAML")
        
    Returns:
        Redirect to WorkOS SSO page
    """
    workos = WorkOSService(
        api_key=settings.WORKOS_API_KEY,
        client_id=settings.WORKOS_CLIENT_ID,
        redirect_uri=settings.WORKOS_REDIRECT_URI,
    )
    
    # Generate state for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    
    # Get authorization URL
    auth_url = workos.get_authorization_url(
        organization_id=organization_id,
        provider=provider,
        state=state,
    )
    
    return RedirectResponse(url=auth_url)


@router.get("/sso/callback")
async def workos_sso_callback(
    code: str,
    state: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Handle WorkOS SSO callback.
    
    Args:
        code: Authorization code from WorkOS
        state: State parameter for CSRF validation
        
    Returns:
        Authentication response with tokens
    """
    try:
        workos = WorkOSService(
            api_key=settings.WORKOS_API_KEY,
            client_id=settings.WORKOS_CLIENT_ID,
            redirect_uri=settings.WORKOS_REDIRECT_URI,
        )
        
        # Exchange code for profile
        profile_data = await workos.get_profile_and_token(code)
        
        # Find or create user
        result = await db.execute(
            select(User).where(User.workos_user_id == profile_data["workos_user_id"])
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Check if user exists with same email
            result = await db.execute(
                select(User).where(User.email == profile_data["email"])
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Link existing user to WorkOS
                user.workos_user_id = profile_data["workos_user_id"]
                user.email_verified = True  # SSO email is verified
            else:
                # Create new user
                username = profile_data["email"].split('@')[0]
                # Ensure username is unique
                base_username = username
                counter = 1
                while True:
                    result = await db.execute(
                        select(User).where(User.username == username)
                    )
                    if not result.scalar_one_or_none():
                        break
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User(
                    workos_user_id=profile_data["workos_user_id"],
                    email=profile_data["email"],
                    username=username,
                    first_name=profile_data.get("first_name", ""),
                    last_name=profile_data.get("last_name", ""),
                    user_type=UserType.ORG_ADMIN,
                    is_active=True,
                    email_verified=True,
                )
                db.add(user)
                await db.flush()
        
        # Handle organization linking if WorkOS organization ID present
        if profile_data.get("organization_id"):
            # Find or create organization
            result = await db.execute(
                select(Organization).where(
                    Organization.workos_organization_id == profile_data["organization_id"]
                )
            )
            organization = result.scalar_one_or_none()
            
            if not organization:
                # Fetch organization details from WorkOS
                org_data = await workos.get_organization(profile_data["organization_id"])
                
                workspace = org_data["name"].lower().replace(' ', '-')
                import random
                workspace = f"{workspace}-{random.randint(1000, 9999)}"
                
                organization = Organization(
                    workos_organization_id=profile_data["organization_id"],
                    name=org_data["name"],
                    workspace=workspace,
                    owner=user.id,
                    is_active=True,
                )
                db.add(organization)
                await db.flush()
            
            # Add user to organization if not already member
            result = await db.execute(
                select(OrganizationUsers).where(
                    OrganizationUsers.user_id == user.id,
                    OrganizationUsers.organization_id == organization.id,
                )
            )
            membership = result.scalar_one_or_none()
            
            if not membership:
                membership = OrganizationUsers(
                    user_id=user.id,
                    organization_id=organization.id,
                    role=OrganizationRoles.MEMBER,  # Default role
                )
                db.add(membership)
        
        await db.commit()
        await db.refresh(user)
        
        # Create session
        ip_address = request.client.host if request and request.client else None
        user_agent = request.headers.get("user-agent") if request else None
        
        session = await create_user_session(
            db, user, ip_address, user_agent
        )
        
        # Generate tokens
        tokens = create_token_pair(
            user_id=user.id,
            email=user.email,
            username=user.username,
            user_type=user.user_type.value,
            secret_key=settings.JWT_SECRET,
            session_id=session.id,
            workos_user_id=user.workos_user_id,
        )
        
        logger.info(f"User {user.id} logged in via WorkOS SSO")
        
        return {
            **tokens,
            "user": user_to_dict(user),
        }
        
    except Exception as e:
        logger.error(f"WorkOS SSO callback error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSO authentication failed",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
):
    """
    Get current authenticated user information.
    
    Requires:
        Valid JWT token in Authorization header
        
    Returns:
        User information
    """
    user = request.scope.get("user")
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    
    return user_to_dict(user)


@router.post("/verify-email")
async def verify_email(
    verification: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Verify user email address.
    
    Args:
        verification: Email verification token
        
    Returns:
        Success message
    """
    try:
        # Verify token
        payload = verify_jwt_token(
            verification.token,
            settings.JWT_SECRET,
        )
        
        user_id = payload.get("user_id")
        if not user_id or payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
            )
        
        # Load user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Mark email as verified
        user.email_verified = True
        await db.commit()
        
        logger.info(f"User {user.id} email verified")
        
        return {"message": "Email verified successfully"}
        
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )


@router.post("/forgot-password")
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Request password reset email.
    
    Args:
        reset_request: Password reset request with email
        
    Returns:
        Success message (always returns success to prevent email enumeration)
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == reset_request.email)
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Generate password reset token
        # TODO: Send email with reset link
        # For now, just log it
        logger.info(f"Password reset requested for user {user.id}")
    
    # Always return success to prevent email enumeration
    return {
        "message": "If the email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    reset_confirm: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Reset password with token.
    
    Args:
        reset_confirm: Password reset confirmation with token and new password
        
    Returns:
        Success message
    """
    try:
        # Verify token
        payload = verify_jwt_token(
            reset_confirm.token,
            settings.JWT_SECRET,
        )
        
        user_id = payload.get("user_id")
        if not user_id or payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token",
            )
        
        # Load user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Update password
        user.password_hash = hash_password(reset_confirm.new_password)
        await db.commit()
        
        logger.info(f"User {user.id} password reset successfully")
        
        return {"message": "Password reset successfully"}
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
