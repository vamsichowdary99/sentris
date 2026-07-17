from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.alert import Alert, AlertEvent
from app.models.enums import AIEntityType, AlertStatus, IOCType, MitreMappingSource, Severity
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.alert import AlertRepository
from app.repositories.audit_log import AuditLogRepository
from app.repositories.ioc import IOCRepository
from app.repositories.mitre import MitreRepository
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.alert import (
    AlertCreate,
    AlertDetail,
    AlertMitreMappingRead,
    AlertRead,
    AlertUpdate,
)
from app.schemas.ioc import EnrichmentRead, IOCDetail, IOCRead
from app.schemas.mitre import MitreTechniqueRead
from app.services.mitre_rules import RULE_CONFIDENCE, match_techniques

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AlertRepository(session)
        self.ioc_repo = IOCRepository(session)
        self.mitre_repo = MitreRepository(session)
        self.ai_analysis_repo = AIAnalysisRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def create(self, org_id: uuid.UUID, data: AlertCreate) -> Alert:
        fields = data.model_dump()
        if fields.get("src_ip") is not None:
            fields["src_ip"] = str(fields["src_ip"])
        if fields.get("dst_ip") is not None:
            fields["dst_ip"] = str(fields["dst_ip"])

        alert = await self.repo.create(org_id, **fields)
        await self._extract_iocs(org_id, alert)
        await self._apply_rule_based_mitre_mapping(alert)
        await self.session.commit()
        await self.session.refresh(alert)
        self._dispatch_enrichment(alert.id)
        self._dispatch_summarize(org_id, alert.id)
        return alert

    def _dispatch_enrichment(self, alert_id: uuid.UUID) -> None:
        # Fire-and-forget: ingestion must always succeed even if the broker
        # is briefly unreachable, since enrichment is best-effort/eventual.
        from app.workers.tasks.enrichment import enrich_alert_task

        try:
            enrich_alert_task.delay(str(alert_id))
        except Exception:
            logger.warning(
                "Failed to enqueue enrichment task for alert %s", alert_id, exc_info=True
            )

    def _dispatch_summarize(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> None:
        # Same fire-and-forget contract as enrichment — and if no AI provider
        # is configured/reachable, the task simply fails without a summary
        # ever appearing, which is the intended graceful degradation.
        from app.workers.tasks.ai_analysis import summarize_alert_task

        try:
            summarize_alert_task.delay(str(alert_id), str(org_id))
        except Exception:
            logger.warning(
                "Failed to enqueue AI summarize task for alert %s", alert_id, exc_info=True
            )

    # Field names commonly used by Wazuh/Sysmon/Suricata-style event payloads
    # for a domain/hash observable — targeted extraction avoids the false
    # positives a blind regex over free-text raw fields (e.g. file paths
    # like "svchost_update.exe") would produce.
    _DOMAIN_KEYS = frozenset({"dns_query", "domain", "resolved_domain", "c2_domain"})
    _HASH_KEYS = frozenset({"sha256", "sha1", "md5", "file_hash"})

    def _walk_raw(self, raw: dict[str, Any]) -> Iterator[tuple[str, str]]:
        for key, value in raw.items():
            if isinstance(value, str):
                yield key, value
            elif isinstance(value, dict):
                yield from self._walk_raw(value)

    async def _extract_iocs(self, org_id: uuid.UUID, alert: Alert) -> None:
        for ip in (alert.src_ip, alert.dst_ip):
            if ip is None:
                continue
            ioc = await self.ioc_repo.get_or_create(org_id, type=IOCType.ip, value=str(ip))
            await self.ioc_repo.link_to_alert(alert.id, ioc.id)

        for key, value in self._walk_raw(alert.raw):
            if key in self._DOMAIN_KEYS:
                ioc = await self.ioc_repo.get_or_create(org_id, type=IOCType.domain, value=value)
                await self.ioc_repo.link_to_alert(alert.id, ioc.id)
            elif key in self._HASH_KEYS:
                ioc = await self.ioc_repo.get_or_create(
                    org_id, type=IOCType.hash, value=value.lower()
                )
                await self.ioc_repo.link_to_alert(alert.id, ioc.id)

    async def _apply_rule_based_mitre_mapping(self, alert: Alert) -> None:
        for technique_id in match_techniques(alert.title, alert.rule_name):
            # Reference data may not be seeded yet (fresh CI/dev DB) — skip
            # rather than FK-violate on an unseeded technique_id.
            if await self.mitre_repo.get(technique_id) is None:
                continue
            await self.mitre_repo.map_alert(
                alert.id, technique_id, source=MitreMappingSource.rule, confidence=RULE_CONFIDENCE
            )

    async def get(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> Alert:
        alert = await self.repo.get(org_id, alert_id)
        if alert is None:
            raise NotFoundError(f"Alert {alert_id} not found")
        return alert

    async def get_detail(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> AlertDetail:
        alert = await self.get(org_id, alert_id)

        ioc_details = []
        for ioc in await self.ioc_repo.list_for_alert(alert.id):
            enrichments = await self.ioc_repo.list_enrichments(ioc.id)
            ioc_details.append(
                IOCDetail(
                    **IOCRead.model_validate(ioc).model_dump(),
                    enrichments=[EnrichmentRead.model_validate(e) for e in enrichments],
                )
            )

        mitre_mappings = [
            AlertMitreMappingRead(
                technique=MitreTechniqueRead.model_validate(technique),
                source=mapping.source,
                confidence=mapping.confidence,
            )
            for technique, mapping in await self.mitre_repo.list_for_alert(alert.id)
        ]

        ai_analyses = await self.ai_analysis_repo.list_for_entity(AIEntityType.alert, alert.id)

        return AlertDetail(
            **AlertRead.model_validate(alert).model_dump(),
            raw=alert.raw,
            iocs=ioc_details,
            mitre=mitre_mappings,
            ai_analyses=[AIAnalysisRead.model_validate(a) for a in ai_analyses],
        )

    async def update(
        self,
        org_id: uuid.UUID,
        alert_id: uuid.UUID,
        data: AlertUpdate,
        actor_id: uuid.UUID | None = None,
    ) -> Alert:
        alert = await self.get(org_id, alert_id)
        fields = data.model_dump(exclude_unset=True)
        alert = await self.repo.update(alert, **fields)
        await self.audit_repo.create(
            org_id,
            action="alert.update",
            entity_type="alert",
            user_id=actor_id,
            entity_id=alert.id,
            meta={k: str(v) for k, v in fields.items()},
        )
        await self.session.commit()
        return alert

    async def list_page(
        self,
        org_id: uuid.UUID,
        offset: int,
        limit: int,
        status: AlertStatus | None = None,
        severity: Severity | None = None,
        source: str | None = None,
        src_ip: str | None = None,
        q: str | None = None,
        mitre: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> tuple[list[Alert], int]:
        return await self.repo.list_page(
            org_id,
            offset,
            limit,
            status=status,
            severity=severity,
            source=source,
            src_ip=src_ip,
            q=q,
            mitre=mitre,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )

    async def list_events(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> list[AlertEvent]:
        await self.get(org_id, alert_id)
        return await self.repo.list_events(alert_id)
