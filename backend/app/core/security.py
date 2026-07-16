from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


TokenType = Literal["access", "refresh"]


def create_access_token(user_id: str, org_id: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": user_id, "org_id": org_id, "type": "access", "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def generate_refresh_token() -> str:
    """Refresh tokens are opaque random strings, not JWTs — only their hash
    is stored, so a stolen DB dump can't be used to mint sessions."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # SHA-256, not Argon2: the token already carries 48 bytes of entropy,
    # so a slow KDF (meant to defend low-entropy passwords) just adds
    # needless CPU cost to every refresh request.
    return hashlib.sha256(token.encode()).hexdigest()


def verify_refresh_token(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(hash_refresh_token(token), token_hash)


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
