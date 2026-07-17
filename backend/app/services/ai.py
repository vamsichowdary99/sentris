from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.guardrails import wrap_untrusted
from app.ai.router import LLMResponse
from app.ai.structured import run_structured
from app.core.errors import NotFoundError
from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.case import Case
from app.models.enums import AIEntityType, AITask, MitreMappingSource, ReportFormat
from app.models.report import Report
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.alert import AlertRepository
from app.repositories.case import CaseRepository
from app.repositories.ioc import IOCRepository
from app.repositories.mitre import MitreRepository
from app.repositories.report import ReportRepository
from app.schemas.ai import (
    AlertPriorityResult,
    AlertsPrioritizeOutput,
    AlertSummaryOutput,
    AlertTriageOutput,
    CaseReportOutput,
    InvestigationStepsOutput,
    IOCSummaryOutput,
    MitreMappingOutput,
    NLSearchFilter,
    TechniqueExplainOutput,
)

T = TypeVar("T", bound=BaseModel)


class AIService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai_repo = AIAnalysisRepository(session)
        self.alert_repo = AlertRepository(session)
        self.case_repo = CaseRepository(session)
        self.ioc_repo = IOCRepository(session)
        self.mitre_repo = MitreRepository(session)
        self.report_repo = ReportRepository(session)

    # --- shared plumbing ---------------------------------------------------

    async def _run_structured(
        self, task: str, schema: type[T], **prompt_ctx: object
    ) -> tuple[T, LLMResponse, str]:
        return await run_structured(task, schema, **prompt_ctx)

    async def _store(
        self,
        entity_type: AIEntityType,
        entity_id: uuid.UUID,
        task: AITask,
        response: LLMResponse,
        version: str,
        output: dict[str, Any],
    ) -> AIAnalysis:
        record = await self.ai_repo.create(
            entity_type=entity_type,
            entity_id=entity_id,
            task=task,
            model=response.model,
            provider=response.provider,
            prompt_version=version,
            output=output,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            latency_ms=response.latency_ms,
        )
        await self.session.commit()
        return record

    async def _get_alert(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> Alert:
        alert = await self.alert_repo.get(org_id, alert_id)
        if alert is None:
            raise NotFoundError(f"Alert {alert_id} not found")
        return alert

    def _alert_text(self, alert: Alert) -> str:
        return json.dumps(
            {
                "title": alert.title,
                "source": alert.source,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "src_ip": str(alert.src_ip) if alert.src_ip else None,
                "dst_ip": str(alert.dst_ip) if alert.dst_ip else None,
                "user_subject": alert.user_subject,
                "occurred_at": alert.occurred_at.isoformat(),
                "raw": alert.raw,
            },
            default=str,
        )

    # --- single-alert tasks --------------------------------------------

    async def summarize_alert(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> AIAnalysis:
        alert = await self._get_alert(org_id, alert_id)
        ctx = {"untrusted_alert": wrap_untrusted("alert", self._alert_text(alert))}
        parsed, response, version = await self._run_structured(
            "summary", AlertSummaryOutput, **ctx
        )
        return await self._store(
            AIEntityType.alert, alert.id, AITask.summary, response, version, parsed.model_dump()
        )

    async def triage_alert(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> AIAnalysis:
        alert = await self._get_alert(org_id, alert_id)
        ctx = {"untrusted_alert": wrap_untrusted("alert", self._alert_text(alert))}
        parsed, response, version = await self._run_structured("triage", AlertTriageOutput, **ctx)
        record = await self._store(
            AIEntityType.alert, alert.id, AITask.triage, response, version, parsed.model_dump()
        )
        await self.alert_repo.update(alert, ai_severity=parsed.severity, priority=parsed.priority)
        await self.session.commit()
        return record

    async def investigate_alert(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> AIAnalysis:
        alert = await self._get_alert(org_id, alert_id)
        ctx = {"untrusted_alert": wrap_untrusted("alert", self._alert_text(alert))}
        parsed, response, version = await self._run_structured(
            "steps", InvestigationStepsOutput, **ctx
        )
        return await self._store(
            AIEntityType.alert, alert.id, AITask.steps, response, version, parsed.model_dump()
        )

    async def map_alert_mitre(self, org_id: uuid.UUID, alert_id: uuid.UUID) -> AIAnalysis:
        alert = await self._get_alert(org_id, alert_id)
        techniques, _ = await self.mitre_repo.list_page(0, 500)
        catalog = "\n".join(
            f"{t.id}: {t.name} ({t.tactic}) — {t.description[:120]}" for t in techniques
        )
        ctx = {
            "untrusted_alert": wrap_untrusted("alert", self._alert_text(alert)),
            "technique_catalog": catalog,
        }
        parsed, response, version = await self._run_structured("mitre", MitreMappingOutput, **ctx)

        valid_ids = {t.id for t in techniques}
        applied: list[str] = []
        for suggestion in parsed.techniques:
            if suggestion.id not in valid_ids:
                continue  # guard against a hallucinated technique ID
            await self.mitre_repo.upsert_mapping(
                alert.id,
                suggestion.id,
                source=MitreMappingSource.ai,
                confidence=suggestion.confidence,
            )
            applied.append(suggestion.id)

        return await self._store(
            AIEntityType.alert,
            alert.id,
            AITask.mitre,
            response,
            version,
            {"techniques": [t.model_dump() for t in parsed.techniques], "applied": applied},
        )

    # --- IOC summary (stateless — Redis-cached in the router, not persisted
    # to ai_analyses since that table's entity_type is scoped to alert/case) --

    async def summarize_ioc(self, org_id: uuid.UUID, ioc_id: uuid.UUID) -> tuple[str, LLMResponse]:
        ioc = await self.ioc_repo.get(org_id, ioc_id)
        if ioc is None:
            raise NotFoundError(f"IOC {ioc_id} not found")
        enrichments = await self.ioc_repo.list_enrichments(ioc.id)
        text = json.dumps(
            {
                "type": ioc.type.value,
                "value": ioc.value,
                "reputation": ioc.reputation,
                "enrichments": [
                    {"provider": e.provider, "verdict": e.verdict, "score": e.score}
                    for e in enrichments
                ],
            },
            default=str,
        )
        ctx = {"untrusted_ioc": wrap_untrusted("ioc", text)}
        parsed, response, _ = await self._run_structured("ioc_summary", IOCSummaryOutput, **ctx)
        return parsed.summary, response

    async def explain_technique(self, technique_id: str) -> tuple[str, LLMResponse]:
        technique = await self.mitre_repo.get(technique_id)
        if technique is None:
            raise NotFoundError(f"MITRE technique {technique_id} not found")
        text = json.dumps(
            {
                "id": technique.id,
                "name": technique.name,
                "tactic": technique.tactic,
                "description": technique.description,
            }
        )
        ctx = {"untrusted_technique": wrap_untrusted("technique", text)}
        parsed, response, _ = await self._run_structured(
            "technique_explain", TechniqueExplainOutput, **ctx
        )
        return parsed.explanation, response

    # --- batch prioritize -------------------------------------------------

    async def prioritize_alerts(
        self, org_id: uuid.UUID, alert_ids: list[uuid.UUID]
    ) -> list[AlertPriorityResult]:
        alerts = []
        for alert_id in alert_ids:
            alert = await self.alert_repo.get(org_id, alert_id)
            if alert is not None:
                alerts.append(alert)
        if not alerts:
            return []

        payload = [{"id": str(a.id), **json.loads(self._alert_text(a))} for a in alerts]
        ctx = {"untrusted_alerts": wrap_untrusted("alerts_batch", json.dumps(payload, default=str))}
        parsed, response, version = await self._run_structured(
            "prioritize", AlertsPrioritizeOutput, **ctx
        )

        by_id = {a.id: a for a in alerts}
        for result in parsed.results:
            try:
                alert_uuid = uuid.UUID(result.id)
            except ValueError:
                continue
            alert = by_id.get(alert_uuid)
            if alert is None:
                continue
            await self.alert_repo.update(
                alert, ai_severity=result.severity, priority=result.priority
            )
            await self.ai_repo.create(
                entity_type=AIEntityType.alert,
                entity_id=alert.id,
                task=AITask.triage,
                model=response.model,
                provider=response.provider,
                prompt_version=version,
                output=result.model_dump(),
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                latency_ms=response.latency_ms,
            )
        await self.session.commit()
        return parsed.results

    # --- case report -------------------------------------------------------

    async def _case_text(self, case: Case) -> str:
        alerts = await self.case_repo.list_alerts(case.id)
        alert_bundle = []
        for alert in alerts:
            mitre = await self.mitre_repo.list_for_alert(alert.id)
            iocs = await self.ioc_repo.list_for_alert(alert.id)
            alert_bundle.append(
                {
                    "title": alert.title,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "source": alert.source,
                    "occurred_at": alert.occurred_at.isoformat(),
                    "src_ip": str(alert.src_ip) if alert.src_ip else None,
                    "dst_ip": str(alert.dst_ip) if alert.dst_ip else None,
                    "mitre": [technique.id for technique, _ in mitre],
                    "iocs": [
                        {"type": ioc.type.value, "value": ioc.value, "reputation": ioc.reputation}
                        for ioc in iocs
                    ],
                }
            )
        timeline = await self.case_repo.list_timeline(case.id)
        return json.dumps(
            {
                "title": case.title,
                "summary": case.summary,
                "status": case.status.value,
                "severity": case.severity.value,
                "opened_at": case.opened_at.isoformat(),
                "alerts": alert_bundle,
                "timeline": [
                    {"kind": t.kind, "description": t.description, "ts": t.ts.isoformat()}
                    for t in timeline
                ],
            },
            default=str,
        )

    async def generate_case_report(
        self, org_id: uuid.UUID, case_id: uuid.UUID, actor_id: uuid.UUID
    ) -> Report:
        case = await self.case_repo.get(org_id, case_id)
        if case is None:
            raise NotFoundError(f"Case {case_id} not found")

        ctx = {"untrusted_case": wrap_untrusted("case", await self._case_text(case))}
        parsed, response, version = await self._run_structured("report", CaseReportOutput, **ctx)

        report = await self.report_repo.create(
            case_id=case.id,
            format=ReportFormat.markdown,
            content=parsed.report_markdown,
            generated_by=actor_id,
        )
        await self.ai_repo.create(
            entity_type=AIEntityType.case,
            entity_id=case.id,
            task=AITask.report,
            model=response.model,
            provider=response.provider,
            prompt_version=version,
            output={"report_id": str(report.id)},
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            latency_ms=response.latency_ms,
        )
        await self.session.commit()
        return report

    # --- natural-language search --------------------------------------------

    async def nl_search(
        self, org_id: uuid.UUID, query: str
    ) -> tuple[NLSearchFilter, list[Alert], int]:
        ctx = {
            "untrusted_query": wrap_untrusted("query", query),
            "now_iso": datetime.now(UTC).isoformat(),
        }
        parsed, _response, _version = await self._run_structured(
            "nl_search", NLSearchFilter, **ctx
        )
        items, total = await self.alert_repo.list_page(
            org_id,
            0,
            50,
            status=parsed.status,
            severity=parsed.severity,
            source=parsed.source,
            src_ip=parsed.src_ip,
            q=parsed.q,
            mitre=parsed.mitre,
            occurred_from=parsed.occurred_from,
            occurred_to=parsed.occurred_to,
        )
        return parsed, items, total
