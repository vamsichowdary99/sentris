from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AlertStatus, Severity
from app.schemas.alert import AlertRead


class AlertSummaryOutput(BaseModel):
    summary: str


class AlertTriageOutput(BaseModel):
    severity: Severity
    priority: int = Field(ge=1, le=100)
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class InvestigationStepsOutput(BaseModel):
    steps: list[str]


class MitreTechniqueSuggestion(BaseModel):
    id: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class MitreMappingOutput(BaseModel):
    techniques: list[MitreTechniqueSuggestion]


class AlertPriorityResult(BaseModel):
    id: str
    severity: Severity
    priority: int = Field(ge=1, le=100)
    reasoning: str


class AlertsPrioritizeOutput(BaseModel):
    results: list[AlertPriorityResult]


class CaseReportOutput(BaseModel):
    report_markdown: str


class IOCSummaryOutput(BaseModel):
    summary: str


class TechniqueExplainOutput(BaseModel):
    explanation: str


class NLSearchFilter(BaseModel):
    """The only shape an NL search query is allowed to compile down to —
    allow-listed fields mirroring AlertRepository.list_page, never raw SQL."""

    status: AlertStatus | None = None
    severity: Severity | None = None
    source: str | None = None
    src_ip: str | None = None
    q: str | None = None
    mitre: str | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None


# --- API request/response shapes ---


class PrioritizeRequest(BaseModel):
    alert_ids: list[str] = Field(min_length=1, max_length=30)


class NLSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class IOCSummaryResponse(BaseModel):
    summary: str
    provider: str
    model: str


class NLSearchResponse(BaseModel):
    filter: NLSearchFilter
    items: list[AlertRead]
    total: int


class AlertsPrioritizeResponse(BaseModel):
    results: list[AlertPriorityResult]


class TechniqueExplainResponse(BaseModel):
    explanation: str
    provider: str
    model: str
