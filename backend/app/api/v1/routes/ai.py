import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org_id, get_current_user_id, require_permission
from app.db.session import get_db_session
from app.schemas.ai import (
    AlertsPrioritizeResponse,
    IOCSummaryResponse,
    NLSearchRequest,
    NLSearchResponse,
    PrioritizeRequest,
    TechniqueExplainResponse,
)
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.alert import AlertRead
from app.schemas.report import ReportRead
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["ai"])

_use = [Depends(require_permission("ai.use"))]


@router.post(
    "/alerts/{alert_id}/summarize", response_model=AIAnalysisRead, dependencies=_use
)
async def summarize_alert(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AIAnalysisRead:
    record = await AIService(db).summarize_alert(org_id, alert_id)
    return AIAnalysisRead.model_validate(record)


@router.post("/alerts/{alert_id}/triage", response_model=AIAnalysisRead, dependencies=_use)
async def triage_alert(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AIAnalysisRead:
    record = await AIService(db).triage_alert(org_id, alert_id)
    return AIAnalysisRead.model_validate(record)


@router.post(
    "/alerts/{alert_id}/investigate", response_model=AIAnalysisRead, dependencies=_use
)
async def investigate_alert(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AIAnalysisRead:
    record = await AIService(db).investigate_alert(org_id, alert_id)
    return AIAnalysisRead.model_validate(record)


@router.post("/alerts/{alert_id}/mitre", response_model=AIAnalysisRead, dependencies=_use)
async def map_alert_mitre(
    alert_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AIAnalysisRead:
    record = await AIService(db).map_alert_mitre(org_id, alert_id)
    return AIAnalysisRead.model_validate(record)


@router.post(
    "/alerts/summarize-batch", response_model=AlertsPrioritizeResponse, dependencies=_use
)
async def prioritize_alerts(
    data: PrioritizeRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> AlertsPrioritizeResponse:
    alert_ids = [uuid.UUID(i) for i in data.alert_ids]
    results = await AIService(db).prioritize_alerts(org_id, alert_ids)
    return AlertsPrioritizeResponse(results=results)


@router.post("/cases/{case_id}/report", response_model=ReportRead, dependencies=_use)
async def generate_case_report(
    case_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> ReportRead:
    report = await AIService(db).generate_case_report(org_id, case_id, user_id)
    return ReportRead.model_validate(report)


@router.post(
    "/mitre/{technique_id}/explain", response_model=TechniqueExplainResponse, dependencies=_use
)
async def explain_technique(
    technique_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> TechniqueExplainResponse:
    explanation, response = await AIService(db).explain_technique(technique_id)
    return TechniqueExplainResponse(
        explanation=explanation, provider=response.provider, model=response.model
    )


@router.post("/iocs/{ioc_id}/summary", response_model=IOCSummaryResponse, dependencies=_use)
async def summarize_ioc(
    ioc_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> IOCSummaryResponse:
    summary, response = await AIService(db).summarize_ioc(org_id, ioc_id)
    return IOCSummaryResponse(summary=summary, provider=response.provider, model=response.model)


@router.post("/search", response_model=NLSearchResponse, dependencies=_use)
async def nl_search(
    data: NLSearchRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db_session),
) -> NLSearchResponse:
    parsed_filter, items, total = await AIService(db).nl_search(org_id, data.query)
    return NLSearchResponse(
        filter=parsed_filter, items=[AlertRead.model_validate(a) for a in items], total=total
    )
