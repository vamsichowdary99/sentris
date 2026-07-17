from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def create(
        self, org_id: uuid.UUID, email: str, password_hash: str, full_name: str
    ) -> User:
        user = User(org_id=org_id, email=email, password_hash=password_hash, full_name=full_name)
        self.session.add(user)
        await self.session.flush()
        return user
