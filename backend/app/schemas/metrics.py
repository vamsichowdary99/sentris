from pydantic import BaseModel


class MetricsOverview(BaseModel):
    total_alerts: int
    total_cases: int
    open_cases: int
    alerts_by_status: dict[str, int]
    alerts_by_severity: dict[str, int]
    cases_by_status: dict[str, int]


class MTTRMetrics(BaseModel):
    average_hours: float | None
    sample_size: int


class MitreHeatmapEntry(BaseModel):
    technique_id: str
    technique_name: str
    tactic: str
    alert_count: int


class AnalystMetrics(BaseModel):
    analyst_id: str
    full_name: str
    assigned_cases: int
    closed_cases: int
