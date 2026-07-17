import asyncio
import logging
import uuid

from celery import Task

from app.services.enrichment import EnrichmentService
from app.workers.celery_app import celery_app
from app.workers.db import worker_session

logger = logging.getLogger(__name__)


@celery_app.task(name="sentris.enrich_alert", bind=True, max_retries=3, default_retry_delay=5)
def enrich_alert_task(self: Task, alert_id: str) -> str:
    try:
        asyncio.run(_enrich_alert(alert_id))
        return "ok"
    except Exception as exc:  # noqa: BLE001 — retried via Celery, then logged
        logger.warning("enrich_alert_task failed for alert_id=%s: %s", alert_id, exc)
        raise self.retry(exc=exc) from exc


async def _enrich_alert(alert_id: str) -> None:
    async with worker_session() as session:
        await EnrichmentService(session).enrich_alert(uuid.UUID(alert_id))
