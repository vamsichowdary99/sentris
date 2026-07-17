import uuid

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
from app.models.enums import CaseStatus
from app.repositories.report import ReportRepository
from app.schemas.alert import AlertRead
from app.schemas.case import (
    CaseCreate,
    CaseDetail,
    CaseRead,
    CaseUpdate,
    LinkAlertsRequest,
)
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page
from app.schemas.report import ReportRead
from app.schemas.timeline import TimelineEventRead
from app.services.case import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])

_read = [Depends(require_permission("case.read"))]
_write = [Depends(require_permission("case.write"))]


@router.get("", response_model=Page[CaseRead], dependencies=_read)
async def list_cases(
    status: CaseStatus | None = None,
    org_id: uuid.UUID = Depends(get_current_org_id),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[CaseRead]:
    service = CaseService(db)
    items, total = await service.list_page(
        org_id, pagination.offset, pagination.limit, status=status
    )
    return Page(
        items=[CaseRead.model_validate(c) for c in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post("", response_model=CaseRead, status_code=201, dependencies=_write)
async def create_case(
    data: CaseCreate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> CaseRead:
    service = CaseService(db)
    case = await service.create(org_id, user_id, data)
    return CaseRead.model_validate(case)


@router.get("/{case_id}", response_model=CaseDetail, dependencies=_read)
async def get_case(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> CaseDetail:
    service = CaseService(db)
    return await service.get_detail(org_id, case_id)


@router.patch("/{case_id}", response_model=CaseRead, dependencies=_write)
async def update_case(
    case_id: uuid.UUID,
    data: CaseUpdate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> CaseRead:
    service = CaseService(db)
    case = await service.update(org_id, case_id, user_id, data)
    return CaseRead.model_validate(case)


@router.get("/{case_id}/alerts", response_model=list[AlertRead], dependencies=_read)
async def list_case_alerts(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[AlertRead]:
    service = CaseService(db)
    await service.get(org_id, case_id)
    alerts = await service.repo.list_alerts(case_id)
    return [AlertRead.model_validate(a) for a in alerts]


@router.post("/{case_id}/alerts", response_model=CaseRead, dependencies=_write)
async def link_case_alerts(
    case_id: uuid.UUID,
    data: LinkAlertsRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> CaseRead:
    service = CaseService(db)
    case = await service.link_alerts(org_id, case_id, user_id, data.alert_ids)
    return CaseRead.model_validate(case)


@router.get("/{case_id}/timeline", response_model=list[TimelineEventRead], dependencies=_read)
async def get_case_timeline(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[TimelineEventRead]:
    service = CaseService(db)
    await service.get(org_id, case_id)
    timeline = await service.repo.list_timeline(case_id)
    return [TimelineEventRead.model_validate(t) for t in timeline]


@router.get("/{case_id}/comments", response_model=list[CommentRead], dependencies=_read)
async def list_case_comments(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[CommentRead]:
    service = CaseService(db)
    await service.get(org_id, case_id)
    comments = await service.repo.list_comments(case_id)
    return [CommentRead.model_validate(c) for c in comments]


@router.post(
    "/{case_id}/comments", response_model=CommentRead, status_code=201, dependencies=_write
)
async def add_case_comment(
    case_id: uuid.UUID,
    data: CommentCreate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> CommentRead:
    service = CaseService(db)
    comment = await service.add_comment(org_id, case_id, user_id, data.body)
    return CommentRead.model_validate(comment)


@router.get("/{case_id}/reports", response_model=list[ReportRead], dependencies=_read)
async def list_case_reports(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[ReportRead]:
    service = CaseService(db)
    await service.get(org_id, case_id)
    reports = await ReportRepository(db).list_for_case(case_id)
    return [ReportRead.model_validate(r) for r in reports]
