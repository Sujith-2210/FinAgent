"""
Authentication Security Utilities
Password hashing and JWT token helpers.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import bcrypt
import jwt

from app.config import get_settings


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str, additional_claims: Dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire_at = datetime.now(timezone.utc) + expires_delta

    payload: Dict[str, Any] = {
        "sub": subject,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload=payload,
        key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    settings = get_settings()
    return jwt.decode(
        jwt=token,
        key=settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
