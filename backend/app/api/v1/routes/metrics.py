import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org_id, require_permission
from app.db.session import get_db_session
from app.schemas.metrics import AnalystMetrics, MetricsOverview, MitreHeatmapEntry, MTTRMetrics
from app.services.metrics import MetricsService

router = APIRouter(
    prefix="/metrics", tags=["metrics"], dependencies=[Depends(require_permission("metrics.read"))]
)


@router.get("/overview", response_model=MetricsOverview)
async def get_overview(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> MetricsOverview:
    return await MetricsService(db).overview(org_id)


@router.get("/mttr", response_model=MTTRMetrics)
async def get_mttr(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> MTTRMetrics:
    return await MetricsService(db).mttr(org_id)


@router.get("/mitre-heatmap", response_model=list[MitreHeatmapEntry])
async def get_mitre_heatmap(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[MitreHeatmapEntry]:
    return await MetricsService(db).mitre_heatmap(org_id)


@router.get("/analyst", response_model=list[AnalystMetrics])
async def get_analyst_metrics(
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[AnalystMetrics]:
    return await MetricsService(db).analyst_workload(org_id)
