from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_token
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.rbac import RBACRepository
from app.repositories.user import UserRepository

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None:
        raise AuthError("Missing authentication token")

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise AuthError("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid token payload")

    user = await UserRepository(db).get(uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise AuthError("User not found or inactive")
    return user


async def get_current_org_id(user: User = Depends(get_current_user)) -> uuid.UUID:
    return user.org_id


async def get_current_user_id(user: User = Depends(get_current_user)) -> uuid.UUID:
    return user.id


def require_permission(code: str) -> Callable[..., Coroutine[None, None, User]]:
    """Route dependency factory: `Depends(require_permission("case.write"))`.
    Layered on top of get_current_user — a request must first present a
    valid access token, then hold the named permission via its role(s)."""

    async def dependency(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ) -> User:
        permissions = await RBACRepository(db).get_user_permissions(user.id)
        if code not in permissions:
            raise ForbiddenError(f"Missing required permission: {code}")
        return user

    return dependency


@dataclass
class Pagination:
    page: int
    size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def pagination_params(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=200),
) -> Pagination:
    return Pagination(page=page, size=size)
