import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    Pagination,
    get_current_org_id,
    get_current_user_id,
    pagination_params,
    require_permission,
)
from app.db.session import get_db_session
from app.models.enums import AlertStatus, Severity
from app.schemas.alert import (
    AlertCreate,
    AlertDetail,
    AlertEventRead,
    AlertRead,
    AlertUpdate,
)
from app.schemas.common import Page
from app.services.alert import AlertService
from app.services.enrichment import EnrichmentService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get(
    "", response_model=Page[AlertRead], dependencies=[Depends(require_permission("alert.read"))]
)
async def list_alerts(
    status: AlertStatus | None = None,
    severity: Severity | None = None,
    source: str | None = None,
    src_ip: str | None = None,
    q: str | None = None,
    mitre: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    org_id: uuid.UUID = Depends(get_current_org_id),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[AlertRead]:
    service = AlertService(db)
    items, total = await service.list_page(
        org_id,
        pagination.offset,
        pagination.limit,
        status=status,
        severity=severity,
        source=source,
        src_ip=src_ip,
        q=q,
        mitre=mitre,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    return Page(
        items=[AlertRead.model_validate(a) for a in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post(
    "",
    response_model=AlertRead,
    status_code=201,
    dependencies=[Depends(require_permission("alert.write"))],
)
async def create_alert(
    data: AlertCreate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AlertRead:
    service = AlertService(db)
    alert = await service.create(org_id, data)
    return AlertRead.model_validate(alert)


@router.post(
    "/bulk",
    response_model=list[AlertRead],
    status_code=201,
    dependencies=[Depends(require_permission("alert.write"))],
)
async def bulk_create_alerts(
    data: list[AlertCreate],
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[AlertRead]:
    service = AlertService(db)
    alerts = [await service.create(org_id, item) for item in data]
    return [AlertRead.model_validate(a) for a in alerts]


@router.get(
    "/{alert_id}",
    response_model=AlertDetail,
    dependencies=[Depends(require_permission("alert.read"))],
)
async def get_alert(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AlertDetail:
    service = AlertService(db)
    return await service.get_detail(org_id, alert_id)


@router.patch(
    "/{alert_id}",
    response_model=AlertRead,
    dependencies=[Depends(require_permission("alert.write"))],
)
async def update_alert(
    alert_id: uuid.UUID,
    data: AlertUpdate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> AlertRead:
    service = AlertService(db)
    alert = await service.update(org_id, alert_id, data, actor_id=user_id)
    return AlertRead.model_validate(alert)


@router.post(
    "/{alert_id}/enrich",
    response_model=AlertDetail,
    dependencies=[Depends(require_permission("alert.write"))],
)
async def enrich_alert(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AlertDetail:
    """Force an immediate (synchronous) re-enrichment of every IOC on this
    alert. New alerts already enrich automatically via the Celery pipeline —
    this exists for analysts who want a fresh verdict on demand."""
    service = AlertService(db)
    alert = await service.get(org_id, alert_id)
    await EnrichmentService(db).enrich_alert(alert.id)
    return await service.get_detail(org_id, alert_id)


@router.get(
    "/{alert_id}/events",
    response_model=list[AlertEventRead],
    dependencies=[Depends(require_permission("alert.read"))],
)
async def get_alert_events(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[AlertEventRead]:
    service = AlertService(db)
    events = await service.list_events(org_id, alert_id)
    return [AlertEventRead.model_validate(e) for e in events]
