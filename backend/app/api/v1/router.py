from fastapi import APIRouter

from app.api.v1.routes import (
    ai,
    alerts,
    assets,
    audit_logs,
    auth,
    cases,
    health,
    integrations,
    investigate,
    iocs,
    metrics,
    mitre,
    search,
)

# users/notifications (Phase 7) are added in a later phase — this
# aggregator is the single place new routers get wired in. Phase 7's
# planned admin CRUD for `/integrations` (webhook/provider config) should
# extend routes/integrations.py rather than creating a second router under
# the same prefix.
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(assets.router)
api_router.include_router(alerts.router)
api_router.include_router(iocs.router)
api_router.include_router(mitre.router)
api_router.include_router(cases.router)
api_router.include_router(metrics.router)
api_router.include_router(search.router)
api_router.include_router(audit_logs.router)
api_router.include_router(ai.router)
api_router.include_router(investigate.router)
api_router.include_router(integrations.router)
