from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.mitre import MitreTechnique
from app.repositories.mitre import MitreRepository


class MitreService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MitreRepository(session)

    async def get(self, technique_id: str) -> MitreTechnique:
        technique = await self.repo.get(technique_id)
        if technique is None:
            raise NotFoundError(f"MITRE technique {technique_id} not found")
        return technique

    async def list_page(
        self, offset: int, limit: int, tactic: str | None = None
    ) -> tuple[list[MitreTechnique], int]:
        return await self.repo.list_page(offset, limit, tactic)
