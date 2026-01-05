"""Authentication and Authorization.

Implements:
- API key authentication
- JWT token validation
- Role-based access control (RBAC)
- Scope-based permissions
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import jwt
import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from gateway.config import settings

logger = structlog.get_logger()

# Security schemes
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

# Valid API keys loaded from environment (comma-separated hashes)
# In production, these should come from a secrets manager or database
_API_KEY_HASHES: set[str] = set()


def _load_api_key_hashes() -> set[str]:
    """Load valid API key hashes from environment."""
    global _API_KEY_HASHES
    if not _API_KEY_HASHES:
        # API keys should be stored as SHA256 hashes
        # Set GOODAI_API_KEY_HASHES as comma-separated hash values
        hash_str = os.environ.get("GOODAI_API_KEY_HASHES", "")
        if hash_str:
            _API_KEY_HASHES = set(h.strip() for h in hash_str.split(",") if h.strip())
    return _API_KEY_HASHES


def _hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def validate_api_key(api_key: str) -> bool:
    """Validate an API key against stored hashes.

    Args:
        api_key: The raw API key to validate

    Returns:
        True if the API key is valid, False otherwise
    """
    if not api_key or not api_key.startswith("gai_"):
        return False

    valid_hashes = _load_api_key_hashes()
    if not valid_hashes:
        # No API keys configured - reject all
        logger.error("api_key_validation_failed", reason="No API key hashes configured")
        return False

    key_hash = _hash_api_key(api_key)

    # Use constant-time comparison to prevent timing attacks
    for valid_hash in valid_hashes:
        if hmac.compare_digest(key_hash, valid_hash):
            return True

    return False


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str  # Subject (user/service ID)
    org_id: str  # Organization ID
    roles: list[str]  # User roles
    scopes: list[str]  # Permission scopes
    exp: datetime  # Expiration
    iat: datetime  # Issued at


class AuthenticatedUser(BaseModel):
    """Authenticated user context."""
    user_id: str
    org_id: str
    roles: list[str]
    scopes: list[str]


def create_access_token(
    user_id: str,
    org_id: str,
    roles: list[str],
    scopes: list[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.jwt_expiry_hours))

    payload = {
        "sub": user_id,
        "org_id": org_id,
        "roles": roles,
        "scopes": scopes,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_current_user(
    api_key: Annotated[Optional[str], Security(api_key_header)] = None,
    bearer: Annotated[Optional[HTTPAuthorizationCredentials], Security(bearer_scheme)] = None,
) -> AuthenticatedUser:
    """Extract and validate user from request credentials.

    Supports both API key and JWT bearer token authentication.
    """
    # Try API key first
    if api_key:
        if validate_api_key(api_key):
            logger.info("api_key_auth_success", key_prefix=api_key[:8])
            return AuthenticatedUser(
                user_id="api_key_user",
                org_id="default",
                roles=["api_user"],
                scopes=["agents:read", "agents:execute", "tasks:read", "tasks:write"],
            )
        logger.warning("api_key_auth_failed", key_prefix=api_key[:8] if api_key else "none")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Try bearer token
    if bearer:
        payload = decode_token(bearer.credentials)
        return AuthenticatedUser(
            user_id=payload.sub,
            org_id=payload.org_id,
            roles=payload.roles,
            scopes=payload.scopes,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scope(required_scope: str):
    """Dependency to require a specific scope."""
    async def check_scope(user: Annotated[AuthenticatedUser, Depends(get_current_user)]):
        if required_scope not in user.scopes and "*" not in user.scopes:
            logger.warning(
                "insufficient_scope",
                user_id=user.user_id,
                required=required_scope,
                available=user.scopes,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required_scope}' required",
            )
        return user
    return check_scope


def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def check_role(user: Annotated[AuthenticatedUser, Depends(get_current_user)]):
        if required_role not in user.roles and "admin" not in user.roles:
            logger.warning(
                "insufficient_role",
                user_id=user.user_id,
                required=required_role,
                available=user.roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user
    return check_role
