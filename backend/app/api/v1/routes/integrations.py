from fastapi import APIRouter, Depends

from app.core.deps import require_permission
from app.integrations.investigate_registry import list_provider_statuses
from app.schemas.integrations import IntegrationStatusRead

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get(
    "/status",
    response_model=list[IntegrationStatusRead],
    dependencies=[Depends(require_permission("ioc.read"))],
)
async def get_integration_statuses() -> list[IntegrationStatusRead]:
    return await list_provider_statuses()
