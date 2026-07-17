from enum import StrEnum


class Severity(StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(StrEnum):
    new = "new"
    triaging = "triaging"
    investigating = "investigating"
    closed = "closed"
    false_positive = "false_positive"


class CaseStatus(StrEnum):
    open = "open"
    investigating = "investigating"
    contained = "contained"
    closed = "closed"


class AssetCriticality(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IOCType(StrEnum):
    ip = "ip"
    domain = "domain"
    hash = "hash"
    url = "url"


class MitreMappingSource(StrEnum):
    ai = "ai"
    rule = "rule"
    analyst = "analyst"


class AIEntityType(StrEnum):
    alert = "alert"
    case = "case"
    ioc = "ioc"


class AITask(StrEnum):
    summary = "summary"
    triage = "triage"
    steps = "steps"
    report = "report"
    mitre = "mitre"
    nl_search = "nl_search"


class CommentEntityType(StrEnum):
    alert = "alert"
    case = "case"


class ReportFormat(StrEnum):
    markdown = "markdown"
    pdf = "pdf"


class NotificationType(StrEnum):
    new_case = "new_case"
    case_assigned = "case_assigned"
    ai_report_ready = "ai_report_ready"
    system = "system"


class IntegrationKind(StrEnum):
    virustotal = "virustotal"
    abuseipdb = "abuseipdb"
    shodan = "shodan"
    wazuh = "wazuh"
    slack = "slack"
    discord = "discord"


class AutomationStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
