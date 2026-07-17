from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sentris",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

@celery_app.task(name="sentris.ping")
def ping() -> str:
    """Smoke-test task — confirms the worker is wired to the broker."""
    return "pong"


# Imported after celery_app is defined (task modules import it back) so task
# modules register themselves. Phase 6 AI tasks will add their own import here.
from app.workers import tasks  # noqa: E402,F401
