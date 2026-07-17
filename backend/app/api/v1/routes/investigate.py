import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org_id, get_current_user_id, require_permission
from app.core.rate_limit import limiter
from app.db.session import get_db_session
from app.models.enums import IOCType
from app.models.ioc import IOC
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.alert import AlertRead
from app.schemas.case import CaseRead
from app.schemas.investigate import (
    InvestigateDetailResponse,
    InvestigateReportRequest,
    InvestigateReportResponse,
    InvestigateRequest,
    InvestigateResponse,
    ProviderOutcome,
)
from app.schemas.ioc import IOCRead
from app.services.investigate import InvestigateService

router = APIRouter(prefix="/investigate", tags=["investigate"])

_read = [Depends(require_permission("ioc.read"))]
_write = [Depends(require_permission("ioc.write"))]
_use_ai = [Depends(require_permission("ai.use"))]


def _to_response(
    ioc: IOC, detected_type: IOCType, outcomes: list[ProviderOutcome]
) -> InvestigateResponse:
    return InvestigateResponse(
        ioc=IOCRead.model_validate(ioc),
        detected_type=detected_type,
        providers=outcomes,
    )


@router.post("", response_model=InvestigateResponse, dependencies=_write)
@limiter.limit("15/minute")
async def investigate(
    request: Request,
    data: InvestigateRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> InvestigateResponse:
    service = InvestigateService(db)
    ioc, outcomes = await service.investigate(org_id, data.indicator, user_id)
    return _to_response(ioc, ioc.type, outcomes)


@router.get("/{ioc_id}", response_model=InvestigateDetailResponse, dependencies=_read)
async def get_investigation(
    ioc_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> InvestigateDetailResponse:
    service = InvestigateService(db)
    ioc, outcomes, related_alerts, related_cases, latest_report = await service.get_detail(
        org_id, ioc_id
    )
    return InvestigateDetailResponse(
        ioc=IOCRead.model_validate(ioc),
        detected_type=ioc.type,
        providers=outcomes,
        related_alerts=[AlertRead.model_validate(a) for a in related_alerts],
        related_cases=[CaseRead.model_validate(c) for c in related_cases],
        latest_report=AIAnalysisRead.model_validate(latest_report).model_dump()
        if latest_report
        else None,
    )


@router.post("/{ioc_id}/refresh", response_model=InvestigateResponse, dependencies=_write)
@limiter.limit("15/minute")
async def refresh_investigation(
    request: Request,
    ioc_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> InvestigateResponse:
    service = InvestigateService(db)
    ioc, outcomes = await service.refresh(org_id, ioc_id, user_id)
    return _to_response(ioc, ioc.type, outcomes)


@router.post("/report", response_model=InvestigateReportResponse, dependencies=_use_ai)
@limiter.limit("10/minute")
async def generate_investigate_report(
    request: Request,
    data: InvestigateReportRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> InvestigateReportResponse:
    service = InvestigateService(db)
    record, related_alerts, related_cases = await service.generate_report(
        org_id, user_id, data.indicator, data.ioc_id
    )
    return InvestigateReportResponse(
        id=record.id,
        ioc_id=record.entity_id,
        model=record.model,
        provider=record.provider,
        prompt_version=record.prompt_version,
        report=record.output,
        related_alerts=[AlertRead.model_validate(a) for a in related_alerts],
        related_cases=[CaseRead.model_validate(c) for c in related_cases],
        created_at=record.created_at,
    )
