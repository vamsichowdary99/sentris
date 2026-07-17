import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import IOCType
from app.schemas.alert import AlertRead
from app.schemas.case import CaseRead
from app.schemas.ioc import IOCRead

ProviderStatus = Literal[
    "ok", "cached", "timeout", "error", "misconfigured", "rate_limited", "scanning"
]


class InvestigateRequest(BaseModel):
    indicator: str = Field(min_length=1, max_length=2048)


class ProviderOutcome(BaseModel):
    provider: str
    status: ProviderStatus
    verdict: str | None = None
    score: float | None = None
    raw: dict[str, Any] = {}
    fetched_at: datetime | None = None


class InvestigateResponse(BaseModel):
    ioc: IOCRead
    detected_type: IOCType
    providers: list[ProviderOutcome]


class InvestigateDetailResponse(InvestigateResponse):
    related_alerts: list[AlertRead] = []
    related_cases: list[CaseRead] = []
    latest_report: dict[str, Any] | None = None


class InvestigateReportRequest(BaseModel):
    indicator: str | None = None
    ioc_id: uuid.UUID | None = None


# --- AI-synthesized report structure (validated JSON) ---


class ReportAttribution(BaseModel):
    malware_family: str | None = None
    campaign: str | None = None
    threat_actor: str | None = None
    summary: str


class ReportContext(BaseModel):
    geo: str | None = None
    asn: str | None = None
    first_seen: str | None = None
    last_seen: str | None = None
    scanner_classification: str | None = None
    exposure: str | None = None


class RecommendedAction(BaseModel):
    action: str
    rationale: str


class InvestigateReportOutput(BaseModel):
    verdict: Literal["malicious", "suspicious", "benign", "unknown"]
    confidence: float = Field(ge=0, le=1)
    rationale: str
    attribution: ReportAttribution
    evidence: list[str]
    context: ReportContext
    conflicts: list[str]
    recommended_actions: list[RecommendedAction]


class InvestigateReportResponse(BaseModel):
    id: uuid.UUID
    ioc_id: uuid.UUID
    model: str
    provider: str
    prompt_version: str
    report: InvestigateReportOutput
    related_alerts: list[AlertRead] = []
    related_cases: list[CaseRead] = []
    created_at: datetime
