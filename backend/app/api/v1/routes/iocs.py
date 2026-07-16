import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination, get_current_org_id, pagination_params, require_permission
from app.db.session import get_db_session
from app.schemas.common import Page
from app.schemas.ioc import EnrichmentRead, IOCCreate, IOCDetail, IOCRead
from app.services.ioc import IOCService

router = APIRouter(prefix="/iocs", tags=["iocs"])


@router.get(
    "", response_model=Page[IOCRead], dependencies=[Depends(require_permission("ioc.read"))]
)
async def list_iocs(
    org_id: uuid.UUID = Depends(get_current_org_id),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[IOCRead]:
    service = IOCService(db)
    items, total = await service.list_page(org_id, pagination.offset, pagination.limit)
    return Page(
        items=[IOCRead.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post(
    "",
    response_model=IOCRead,
    status_code=201,
    dependencies=[Depends(require_permission("ioc.write"))],
)
async def create_ioc(
    data: IOCCreate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> IOCRead:
    service = IOCService(db)
    ioc = await service.create(org_id, data)
    return IOCRead.model_validate(ioc)


@router.get(
    "/{ioc_id}", response_model=IOCDetail, dependencies=[Depends(require_permission("ioc.read"))]
)
async def get_ioc(
    ioc_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> IOCDetail:
    service = IOCService(db)
    ioc = await service.get(org_id, ioc_id)
    enrichments = await service.get_enrichments(ioc.id)
    return IOCDetail(
        **IOCRead.model_validate(ioc).model_dump(),
        enrichments=[EnrichmentRead.model_validate(e) for e in enrichments],
    )
