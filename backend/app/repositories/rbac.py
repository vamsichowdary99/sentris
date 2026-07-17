from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission, Role, RolePermission, UserRole


class RBACRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        stmt = (
            pg_insert(UserRole)
            .values(user_id=user_id, role_id=role_id)
            .on_conflict_do_nothing()
        )
        await self.session.execute(stmt)

    async def get_user_roles(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(
                UserRole.user_id == user_id
            )
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_user_permissions(self, user_id: uuid.UUID) -> set[str]:
        stmt = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return set((await self.session.execute(stmt)).scalars().all())
