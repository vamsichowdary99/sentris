from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis
from app.models.enums import AIEntityType, AITask


class AIAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        entity_type: AIEntityType,
        entity_id: uuid.UUID,
        task: AITask,
        model: str,
        provider: str,
        prompt_version: str,
        output: dict[str, Any],
        tokens_in: int | None,
        tokens_out: int | None,
        latency_ms: int | None,
    ) -> AIAnalysis:
        record = AIAnalysis(
            entity_type=entity_type,
            entity_id=entity_id,
            task=task,
            model=model,
            provider=provider,
            prompt_version=prompt_version,
            output=output,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_for_entity(
        self, entity_type: AIEntityType, entity_id: uuid.UUID
    ) -> list[AIAnalysis]:
        stmt = (
            select(AIAnalysis)
            .where(
                AIAnalysis.entity_type == entity_type,
                AIAnalysis.entity_id == entity_id,
            )
            .order_by(AIAnalysis.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
