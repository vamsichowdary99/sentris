# Sentris Architecture

Sentris is a normal 3-tier web app with an AI/enrichment layer bolted onto
the write path. Nothing here is exotic; the interesting decisions are in
*how the AI and integration layers degrade gracefully to zero external
dependencies.*

## Components

```
Next.js frontend  →  FastAPI API  →  PostgreSQL
                          │
                          ├─ Celery workers ← Redis (broker + cache)
                          │      │
                          │      ├─ AI layer (LiteLLM router)
                          │      └─ Integration layer (VT/AbuseIPDB/Shodan/Wazuh)
                          │
                     Alert simulator (replays sample Wazuh/Sysmon/Suricata data)
```

- **Frontend** — Next.js 15 App Router, server components where possible,
  client components for interactive alert/case views. Talks to the API
  over REST (`NEXT_PUBLIC_API_BASE_URL`) and a WebSocket for the live feed.
- **API** — FastAPI, async end-to-end. Owns auth, RBAC, validation, and
  orchestrates the service layer. Never talks to LLM providers or threat-intel
  APIs directly from the request path for anything slow — those are
  dispatched to Celery so the API stays responsive.
- **Workers** — Celery tasks run the alert pipeline: ingest → enrich →
  MITRE-map → AI-summarize. Redis is both the broker and the response cache
  for AI/enrichment calls (see below).
- **Database** — PostgreSQL 16, one normalized schema (see the ER model in
  [`ENGINEERING_PLAN.md`](ENGINEERING_PLAN.md) §4), `pg_trgm` for fuzzy IOC/hostname search,
  full-text `tsvector` columns for alert/case search. `pgvector` is an
  optional follow-up migration for semantic search — deliberately not in the
  base schema (see note below).

## Why these choices

- **FastAPI over Django/Flask** — async-native, Pydantic is the same
  library used for LLM-output validation, so request schemas and AI-output
  schemas share one mental model. Auto-generated OpenAPI docs double as a
  free API showcase.
- **LiteLLM over a hand-rolled provider client** — one call-site, config-driven
  fallback chain (NVIDIA NIM → Groq → OpenRouter free → Ollama), so the
  entire AI layer can run with zero paid keys and zero network (Ollama) for
  offline demos. See [`docs/adr/0002-litellm-free-first-ai.md`](adr/0002-litellm-free-first-ai.md)
  for the full writeup.
- **Celery + Redis over inline async calls** — threat-intel APIs and LLM
  calls are slow and rate-limited; queuing them keeps alert ingestion fast
  and gives natural retry/backoff semantics.
- **Least-privilege DB roles** — the app connects as `sentris_app` (CRUD
  only, no DDL); Alembic runs as `sentris_migrator`. A compromised app
  process can't alter the schema.

## The Investigate module (Phase 6.5)

An on-demand deep-dive layered on top of the automatic pipeline above,
not a parallel system: `POST /api/v1/investigate` detects an indicator's
type, fans out in parallel (`asyncio.gather`, per-provider timeout) to up
to 5 of 8 possible threat-intel sources depending on type, upserts the
same `iocs`/`enrichments` tables the automatic pipeline uses, and an AI
task synthesizes one verdict across every source — explicitly
reconciling disagreement rather than averaging it away. See
[`docs/adr/0003-mock-first-integrations.md`](adr/0003-mock-first-integrations.md)
for why every provider ships both a real client and a mock, selected
per-provider by key presence alone.

Real-provider failure modes are handled as data, not exceptions: a 404 is
a valid "no data" result, a 401/403 is reported as `misconfigured`, a 429
as `rate_limited` (with `Retry-After` respected and a Redis-backed token
bucket throttling proactively — VirusTotal capped at its documented
~4 req/min), and urlscan.io's genuinely asynchronous submit→poll flow
returns a `scanning` result rather than blocking if a scan isn't ready
yet. One provider's failure never fails the rest of an investigation.

## Deliberate scope cuts

- **No pgvector in the base migration.** The default `postgres:16-alpine`
  image doesn't ship it. Semantic search / alert clustering would swap
  the image for `pgvector/pgvector:pg16` and add the `embedding` column +
  IVFFlat index in a follow-up migration, so the base stack stays
  dependency-light.
- **MITRE seed data is a curated subset** (~48 techniques across all 14
  Enterprise tactics), not a full STIX import — enough to drive the
  dashboard heatmap and AI-mapping demo credibly. A full import is a
  drop-in replacement for `app/db/seeds/mitre_attack.json`.
- **Automation (Phase 7 — auto-case-creation + Slack/Discord webhook on
  critical alerts) is deliberately deferred.** Low visual payoff for a
  portfolio relative to effort: a background webhook firing doesn't
  demo well compared to the Investigate module or the AI copilot.

## Request lifecycle (alert ingest → AI report)

1. Simulator or Wazuh webhook `POST`s an alert → `alerts` row created,
   `status=new`.
2. Celery task enriches any IOCs (IP/hash/domain) via the integration layer
   (mock or real), writes `enrichments` + `iocs` rows.
3. AI task summarizes the alert, maps it to MITRE techniques, and proposes
   investigation steps — each call's input/output is cached in Redis by
   `hash(prompt + model)` and persisted to `ai_analyses` for reproducibility.
4. Analyst reviews in the UI, promotes the alert to a `case`.
5. On demand, an AI task generates a narrative incident report from the
   case + its alerts + timeline, stored in `reports`.

## Observability

`structlog` emits JSON logs with a `request_id` bound via middleware
(`app/main.py`) and propagated through Celery task logs. `/api/v1/health`
is a liveness probe; `/api/v1/health/ready` checks Postgres + Redis
connectivity for readiness gating.
