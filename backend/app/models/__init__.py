"""SQLAlchemy ORM models.

Import every model module here so Alembic's autogenerate (which inspects
`Base.metadata`) and application startup both see the full mapped schema.
"""

from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert, AlertEvent
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.automation import AutomationRun
from app.models.base import Base
from app.models.case import Case, CaseAlert
from app.models.comment import Comment
from app.models.integration import Integration
from app.models.ioc import IOC, AlertIOC, Enrichment
from app.models.mitre import AlertMitreTechnique, MitreTechnique
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.rbac import Permission, RefreshToken, Role, RolePermission, UserRole
from app.models.report import Report
from app.models.saved_search import SavedSearch
from app.models.tag import Tag, Taggable
from app.models.timeline import TimelineEvent
from app.models.user import User

__all__ = [
    "Base",
    "Organization",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "RefreshToken",
    "Asset",
    "Alert",
    "AlertEvent",
    "IOC",
    "AlertIOC",
    "Enrichment",
    "MitreTechnique",
    "AlertMitreTechnique",
    "Case",
    "CaseAlert",
    "AIAnalysis",
    "TimelineEvent",
    "Comment",
    "Report",
    "Notification",
    "Integration",
    "AutomationRun",
    "SavedSearch",
    "Tag",
    "Taggable",
    "AuditLog",
]
