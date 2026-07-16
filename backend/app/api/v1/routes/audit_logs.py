import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Pagination, get_current_org_id, pagination_params, require_permission
from app.db.session import get_db_session
from app.repositories.audit_log import AuditLogRepository
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import Page

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get(
    "",
    response_model=Page[AuditLogRead],
    dependencies=[Depends(require_permission("audit.read"))],
)
async def list_audit_logs(
    org_id: uuid.UUID = Depends(get_current_org_id),
    pagination: Pagination = Depends(pagination_params),
    db: AsyncSession = Depends(get_db_session),
) -> Page[AuditLogRead]:
    repo = AuditLogRepository(db)
    items, total = await repo.list_page(org_id, pagination.offset, pagination.limit)
    return Page(
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )
