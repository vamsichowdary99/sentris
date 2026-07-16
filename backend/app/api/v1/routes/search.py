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
from app.schemas.alert import AlertRead
from app.schemas.common import Page
from app.schemas.search import AlertSearchFilters, SavedSearchCreate, SavedSearchRead
from app.services.search import SearchService

router = APIRouter(
    prefix="/search", tags=["search"], dependencies=[Depends(require_permission("search.read"))]
)


@router.post("", response_model=Page[AlertRead])
async def search_alerts(
    filters: AlertSearchFilters,
    org_id: uuid.UUID = Depends(get_current_org_id),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[AlertRead]:
    service = SearchService(db)
    items, total = await service.search_alerts(org_id, filters, pagination.offset, pagination.limit)
    return Page(
        items=[AlertRead.model_validate(a) for a in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/saved", response_model=list[SavedSearchRead])
async def list_saved_searches(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[SavedSearchRead]:
    service = SearchService(db)
    saved = await service.list_saved(user_id)
    return [SavedSearchRead.model_validate(s) for s in saved]


@router.post("/saved", response_model=SavedSearchRead, status_code=201)
async def create_saved_search(
    data: SavedSearchCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> SavedSearchRead:
    service = SearchService(db)
    saved = await service.save(user_id, data)
    return SavedSearchRead.model_validate(saved)
