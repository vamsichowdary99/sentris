# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r sentris && useradd -r -g sentris -m sentris
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# --- dev: editable install with dev/test deps, live-reload friendly ---
FROM base AS dev
RUN pip install --no-cache-dir -e ".[dev]"
COPY tests ./tests
USER sentris
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- prod: slim runtime image, no dev deps, non-root ---
FROM base AS prod
RUN pip install --no-cache-dir .
USER sentris
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
