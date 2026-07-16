import logging
import sys

import structlog

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure structlog to emit JSON logs, one line per event, with
    request-scoped context (request_id, path, etc.) merged in via
    contextvars — see app.core.deps for where request_id is bound.
    """
    settings = get_settings()
    log_level = logging.DEBUG if not settings.is_production else logging.INFO

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "sentris") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
