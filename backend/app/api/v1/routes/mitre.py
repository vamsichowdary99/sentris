from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination, pagination_params, require_permission
from app.db.session import get_db_session
from app.schemas.common import Page
from app.schemas.mitre import MitreTechniqueRead
from app.services.mitre import MitreService

router = APIRouter(
    prefix="/mitre", tags=["mitre"], dependencies=[Depends(require_permission("mitre.read"))]
)


@router.get("/techniques", response_model=Page[MitreTechniqueRead])
async def list_techniques(
    tactic: str | None = None,
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[MitreTechniqueRead]:
    service = MitreService(db)
    items, total = await service.list_page(pagination.offset, pagination.limit, tactic=tactic)
    return Page(
        items=[MitreTechniqueRead.model_validate(t) for t in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get("/techniques/{technique_id}", response_model=MitreTechniqueRead)
async def get_technique(
    technique_id: str, db: AsyncSession = Depends(get_db_session)
) -> MitreTechniqueRead:
    service = MitreService(db)
    technique = await service.get(technique_id)
    return MitreTechniqueRead.model_validate(technique)
