import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination, get_current_org_id, pagination_params, require_permission
from app.db.session import get_db_session
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.common import Page
from app.services.asset import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get(
    "", response_model=Page[AssetRead], dependencies=[Depends(require_permission("asset.read"))]
)
async def list_assets(
    org_id: uuid.UUID = Depends(get_current_org_id),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[AssetRead]:
    service = AssetService(db)
    items, total = await service.list_page(org_id, pagination.offset, pagination.limit)
    return Page(
        items=[AssetRead.model_validate(a) for a in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.post(
    "",
    response_model=AssetRead,
    status_code=201,
    dependencies=[Depends(require_permission("asset.write"))],
)
async def create_asset(
    data: AssetCreate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AssetRead:
    service = AssetService(db)
    asset = await service.create(org_id, data)
    return AssetRead.model_validate(asset)


@router.get(
    "/{asset_id}",
    response_model=AssetRead,
    dependencies=[Depends(require_permission("asset.read"))],
)
async def get_asset(
    asset_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AssetRead:
    service = AssetService(db)
    asset = await service.get(org_id, asset_id)
    return AssetRead.model_validate(asset)


@router.patch(
    "/{asset_id}",
    response_model=AssetRead,
    dependencies=[Depends(require_permission("asset.write"))],
)
async def update_asset(
    asset_id: uuid.UUID,
    data: AssetUpdate,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AssetRead:
    service = AssetService(db)
    asset = await service.update(org_id, asset_id, data)
    return AssetRead.model_validate(asset)
