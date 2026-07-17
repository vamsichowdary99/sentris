from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails import wrap_untrusted
from app.ai.structured import run_structured
from app.core.config import get_settings
from app.core.errors import InvalidIndicatorError, NotFoundError
from app.integrations.base import VERDICT_RANK, ThreatIntelProvider
from app.integrations.http_helpers import ProviderAuthError, ProviderRateLimitError
from app.integrations.investigate_registry import get_investigate_providers
from app.integrations.provider_health import get_provider_health
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.case import Case
from app.models.enums import AIEntityType, AITask
from app.models.ioc import IOC
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.ioc import IOCRepository
from app.schemas.investigate import InvestigateReportOutput, ProviderOutcome
from app.services.indicator_detect import detect_indicator_type

logger = logging.getLogger(__name__)


class InvestigateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ioc_repo = IOCRepository(session)
        self.ai_repo = AIAnalysisRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def investigate(
        self,
        org_id: uuid.UUID,
        indicator: str,
        actor_id: uuid.UUID,
        force_refresh: bool = False,
    ) -> tuple[IOC, list[ProviderOutcome]]:
        detected = detect_indicator_type(indicator)
        if detected is None:
            raise InvalidIndicatorError(
                f"'{indicator}' isn't a recognizable IP address, domain, URL, or file hash "
                "(MD5/SHA1/SHA256)."
            )
        ioc_type, normalized = detected

        ioc = await self.ioc_repo.get_or_create(org_id, type=ioc_type, value=normalized)
        await self.session.commit()

        providers = get_investigate_providers(ioc_type)
        outcomes = await self._fan_out(ioc, providers, force_refresh)
        await self._update_reputation(ioc, outcomes)
        await self.audit_repo.create(
            org_id,
            action="investigate.run",
            entity_type="ioc",
            user_id=actor_id,
            entity_id=ioc.id,
            meta={"indicator": normalized, "provider_count": len(outcomes)},
        )
        await self.session.commit()
        return ioc, outcomes

    async def refresh(
        self, org_id: uuid.UUID, ioc_id: uuid.UUID, actor_id: uuid.UUID
    ) -> tuple[IOC, list[ProviderOutcome]]:
        ioc = await self._get_ioc(org_id, ioc_id)
        providers = get_investigate_providers(ioc.type)
        outcomes = await self._fan_out(ioc, providers, force_refresh=True)
        await self._update_reputation(ioc, outcomes)
        await self.audit_repo.create(
            org_id,
            action="investigate.refresh",
            entity_type="ioc",
            user_id=actor_id,
            entity_id=ioc.id,
        )
        await self.session.commit()
        return ioc, outcomes

    async def get_detail(
        self, org_id: uuid.UUID, ioc_id: uuid.UUID
    ) -> tuple[IOC, list[ProviderOutcome], list[Alert], list[Case], AIAnalysis | None]:
        ioc = await self._get_ioc(org_id, ioc_id)
        outcomes = [
            ProviderOutcome(
                provider=e.provider,
                status="cached",
                verdict=e.verdict,
                score=e.score,
                raw=e.raw,
                fetched_at=e.fetched_at,
            )
            for e in await self.ioc_repo.list_enrichments(ioc.id)
        ]
        related_alerts = await self.ioc_repo.list_alerts_for_ioc(ioc.id)
        related_cases = await self.ioc_repo.list_cases_for_ioc(ioc.id)
        reports = await self.ai_repo.list_for_entity(AIEntityType.ioc, ioc.id)
        return ioc, outcomes, related_alerts, related_cases, (reports[0] if reports else None)

    async def generate_report(
        self,
        org_id: uuid.UUID,
        actor_id: uuid.UUID,
        indicator: str | None,
        ioc_id: uuid.UUID | None,
    ) -> tuple[AIAnalysis, list[Alert], list[Case]]:
        if ioc_id is not None:
            ioc = await self._get_ioc(org_id, ioc_id)
            outcomes = [
                ProviderOutcome(
                    provider=e.provider,
                    status="cached",
                    verdict=e.verdict,
                    score=e.score,
                    raw=e.raw,
                    fetched_at=e.fetched_at,
                )
                for e in await self.ioc_repo.list_enrichments(ioc.id)
            ]
            if not outcomes:
                providers = get_investigate_providers(ioc.type)
                outcomes = await self._fan_out(ioc, providers, force_refresh=False)
                await self._update_reputation(ioc, outcomes)
                await self.session.commit()
        elif indicator is not None:
            ioc, outcomes = await self.investigate(org_id, indicator, actor_id)
        else:
            raise InvalidIndicatorError("Provide either an indicator or an ioc_id.")

        related_alerts = await self.ioc_repo.list_alerts_for_ioc(ioc.id)
        related_cases = await self.ioc_repo.list_cases_for_ioc(ioc.id)

        evidence = wrap_untrusted(
            "investigation_evidence",
            self._evidence_text(ioc, outcomes, related_alerts, related_cases),
        )
        parsed, response, version = await run_structured(
            "investigate_report", InvestigateReportOutput, untrusted_evidence=evidence
        )

        record = await self.ai_repo.create(
            entity_type=AIEntityType.ioc,
            entity_id=ioc.id,
            task=AITask.report,
            model=response.model,
            provider=response.provider,
            prompt_version=version,
            output=parsed.model_dump(),
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            latency_ms=response.latency_ms,
        )
        await self.audit_repo.create(
            org_id,
            action="investigate.report",
            entity_type="ioc",
            user_id=actor_id,
            entity_id=ioc.id,
        )
        await self.session.commit()
        return record, related_alerts, related_cases

    # --- internals -----------------------------------------------------

    async def _get_ioc(self, org_id: uuid.UUID, ioc_id: uuid.UUID) -> IOC:
        ioc = await self.ioc_repo.get(org_id, ioc_id)
        if ioc is None:
            raise NotFoundError(f"IOC {ioc_id} not found")
        return ioc

    async def _fan_out(
        self, ioc: IOC, providers: list[ThreatIntelProvider], force_refresh: bool
    ) -> list[ProviderOutcome]:
        """Parallel fan-out with a per-provider timeout — every provider's
        outcome (ok/cached/timeout/error/misconfigured/rate_limited/
        scanning) is captured individually, so one slow/broken/throttled
        source never fails the whole investigation."""
        settings = get_settings()
        health = get_provider_health()
        existing_by_provider = {
            e.provider: e for e in await self.ioc_repo.list_enrichments(ioc.id)
        }
        now = datetime.now(UTC)

        async def run_one(provider: ThreatIntelProvider) -> ProviderOutcome:
            existing = existing_by_provider.get(provider.name)
            if not force_refresh and existing is not None:
                # A prior "scanning" result (urlscan mid-poll) is never
                # treated as a fresh cache hit — always check again so a
                # re-run polls the in-flight scan forward.
                still_scanning = existing.raw.get("scan_status") == "in_progress"
                age_seconds = (now - existing.fetched_at).total_seconds()
                if not still_scanning and age_seconds < settings.investigate_cache_ttl_seconds:
                    return ProviderOutcome(
                        provider=provider.name,
                        status="cached",
                        verdict=existing.verdict,
                        score=existing.score,
                        raw=existing.raw,
                        fetched_at=existing.fetched_at,
                    )

            if not provider.is_mock:
                allowed, retry_after = await health.acquire(provider.name)
                if not allowed:
                    return ProviderOutcome(
                        provider=provider.name,
                        status="rate_limited",
                        raw={"retry_after_seconds": retry_after},
                    )

            try:
                result = await asyncio.wait_for(
                    provider.check(ioc.type, ioc.value),
                    timeout=settings.investigate_provider_timeout_seconds,
                )
            except TimeoutError:
                return ProviderOutcome(
                    provider=provider.name, status="timeout", raw={"error": "timed out"}
                )
            except ProviderAuthError as exc:
                if not provider.is_mock:
                    await health.record_status(provider.name, "misconfigured")
                return ProviderOutcome(
                    provider=provider.name, status="misconfigured", raw={"error": str(exc)}
                )
            except ProviderRateLimitError as exc:
                if not provider.is_mock:
                    await health.record_rate_limited(provider.name, exc.retry_after)
                return ProviderOutcome(
                    provider=provider.name,
                    status="rate_limited",
                    raw={"retry_after_seconds": exc.retry_after},
                )
            except Exception as exc:  # noqa: BLE001 — one provider's failure is a partial result
                logger.warning(
                    "investigate.provider_failed provider=%s error=%s", provider.name, exc
                )
                return ProviderOutcome(
                    provider=provider.name, status="error", raw={"error": str(exc)}
                )

            if not provider.is_mock:
                await health.record_success(provider.name)

            enrichment = await self.ioc_repo.upsert_enrichment(
                ioc.id,
                provider=result.provider,
                verdict=result.verdict,
                score=result.score,
                raw=result.raw,
                fetched_at=now,
            )
            status = "scanning" if enrichment.raw.get("scan_status") == "in_progress" else "ok"
            return ProviderOutcome(
                provider=provider.name,
                status=status,
                verdict=enrichment.verdict,
                score=enrichment.score,
                raw=enrichment.raw,
                fetched_at=enrichment.fetched_at,
            )

        return list(await asyncio.gather(*(run_one(p) for p in providers)))

    async def _update_reputation(self, ioc: IOC, outcomes: list[ProviderOutcome]) -> None:
        verdicts = [o.verdict for o in outcomes if o.verdict]
        if not verdicts:
            return
        worst = max(verdicts, key=lambda v: VERDICT_RANK.get(v, 0))
        await self.ioc_repo.update_reputation(ioc, worst, datetime.now(UTC))

    def _evidence_text(
        self,
        ioc: IOC,
        outcomes: list[ProviderOutcome],
        related_alerts: list[Alert],
        related_cases: list[Case],
    ) -> str:
        return json.dumps(
            {
                "indicator": {
                    "type": ioc.type.value,
                    "value": ioc.value,
                    "reputation": ioc.reputation,
                },
                "sources": [
                    {
                        "provider": o.provider,
                        "status": o.status,
                        "verdict": o.verdict,
                        "score": o.score,
                        "raw": o.raw,
                    }
                    for o in outcomes
                ],
                "related_alert_count": len(related_alerts),
                "related_alert_titles": [a.title for a in related_alerts[:10]],
                "related_case_count": len(related_cases),
                "related_case_titles": [c.title for c in related_cases[:10]],
            },
            default=str,
        )
