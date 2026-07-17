import asyncio
import logging
import uuid

from celery import Task

from app.services.ai import AIService
from app.workers.celery_app import celery_app
from app.workers.db import worker_session

logger = logging.getLogger(__name__)


@celery_app.task(name="sentris.summarize_alert", bind=True, max_retries=2, default_retry_delay=15)
def summarize_alert_task(self: Task, alert_id: str, org_id: str) -> str:
    try:
        asyncio.run(_summarize_alert(alert_id, org_id))
        return "ok"
    except Exception as exc:  # noqa: BLE001 — retried via Celery, then logged
        logger.warning("summarize_alert_task failed for alert_id=%s: %s", alert_id, exc)
        raise self.retry(exc=exc) from exc


async def _summarize_alert(alert_id: str, org_id: str) -> None:
    async with worker_session() as session:
        await AIService(session).summarize_alert(uuid.UUID(org_id), uuid.UUID(alert_id))
