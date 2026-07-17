from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthError, ConflictError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models.user import User
from app.repositories.audit_log import AuditLogRepository
from app.repositories.rbac import RBACRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest

DEFAULT_ROLE = "analyst"


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)
        self.rbac_repo = RBACRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def register(
        self,
        org_id: uuid.UUID,
        data: RegisterRequest,
        ip: str | None,
        user_agent: str | None,
    ) -> User:
        if await self.user_repo.get_by_email(data.email) is not None:
            raise ConflictError("Email already registered")

        user = await self.user_repo.create(
            org_id, data.email, hash_password(data.password), data.full_name
        )

        role = await self.rbac_repo.get_role_by_name(DEFAULT_ROLE)
        if role is not None:
            await self.rbac_repo.assign_role(user.id, role.id)

        await self.audit_repo.create(
            org_id,
            action="user.register",
            entity_type="user",
            user_id=user.id,
            entity_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def authenticate(
        self, data: LoginRequest, ip: str | None, user_agent: str | None
    ) -> tuple[User, str, str]:
        user = await self.user_repo.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("This account has been disabled")

        user.last_login_at = datetime.now(UTC)
        access_token = create_access_token(str(user.id), str(user.org_id))
        refresh_token = generate_refresh_token()
        await self.refresh_repo.create(
            user.id, hash_refresh_token(refresh_token), refresh_token_expiry()
        )
        await self.audit_repo.create(
            user.org_id,
            action="auth.login",
            entity_type="user",
            user_id=user.id,
            entity_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        await self.session.commit()
        return user, access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        stored = await self.refresh_repo.get_valid_by_hash(hash_refresh_token(refresh_token))
        if stored is None:
            raise AuthError("Invalid or expired refresh token")

        user = await self.user_repo.get(stored.user_id)
        if user is None or not user.is_active:
            raise AuthError("Invalid or expired refresh token")

        # Rotation: the presented token is single-use — revoke it and issue
        # a fresh one, so a leaked-but-already-used token can't be replayed.
        await self.refresh_repo.revoke(stored)
        new_refresh_token = generate_refresh_token()
        await self.refresh_repo.create(
            user.id, hash_refresh_token(new_refresh_token), refresh_token_expiry()
        )
        access_token = create_access_token(str(user.id), str(user.org_id))
        await self.session.commit()
        return access_token, new_refresh_token

    async def logout(self, refresh_token: str) -> None:
        stored = await self.refresh_repo.get_valid_by_hash(hash_refresh_token(refresh_token))
        if stored is not None:
            await self.refresh_repo.revoke(stored)
            user = await self.user_repo.get(stored.user_id)
            if user is not None:
                await self.audit_repo.create(
                    user.org_id,
                    action="auth.logout",
                    entity_type="user",
                    user_id=user.id,
                    entity_id=user.id,
                )
        await self.session.commit()

    async def get_me(self, user: User) -> tuple[list[str], list[str]]:
        roles = await self.rbac_repo.get_user_roles(user.id)
        permissions = sorted(await self.rbac_repo.get_user_permissions(user.id))
        return roles, permissions
