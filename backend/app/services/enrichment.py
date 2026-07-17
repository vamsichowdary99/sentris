from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import VERDICT_RANK
from app.integrations.registry import get_enrichment_providers
from app.models.ioc import IOC, Enrichment
from app.repositories.ioc import IOCRepository


class EnrichmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ioc_repo = IOCRepository(session)

    async def enrich_ioc(self, ioc: IOC) -> list[Enrichment]:
        fetched_at = datetime.now(UTC)
        enrichments: list[Enrichment] = []
        for provider in get_enrichment_providers(ioc.type):
            result = await provider.check(ioc.type, ioc.value)
            enrichment = await self.ioc_repo.upsert_enrichment(
                ioc.id,
                provider=result.provider,
                verdict=result.verdict,
                score=result.score,
                raw=result.raw,
                fetched_at=fetched_at,
            )
            enrichments.append(enrichment)

        worst_verdict = max(
            (e.verdict for e in enrichments if e.verdict is not None),
            key=lambda v: VERDICT_RANK.get(v, 0),
            default=None,
        )
        if worst_verdict is not None:
            await self.ioc_repo.update_reputation(ioc, worst_verdict, fetched_at)

        return enrichments

    async def enrich_alert(self, alert_id: uuid.UUID) -> list[Enrichment]:
        iocs = await self.ioc_repo.list_for_alert(alert_id)
        results: list[Enrichment] = []
        for ioc in iocs:
            results.extend(await self.enrich_ioc(ioc))
        await self.session.commit()
        return results
