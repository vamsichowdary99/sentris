# ADR 0001: FastAPI (async) over Django/Flask for the backend

## Status
Accepted

## Context
Sentris needed a backend that could (a) serve a normal CRUD REST API for
alerts/cases/IOCs, (b) validate and reason over structured LLM output, and
(c) stay responsive while fanning out to several slow, rate-limited
external APIs per request (VirusTotal, AbuseIPDB, OTX, GreyNoise,
urlscan.io) in the Investigate module. Django and Flask were the two
realistic alternatives given the Python-native security/AI ecosystem.

## Decision
Use FastAPI with SQLAlchemy 2.0's async engine, end-to-end.

## Rationale
- **Native async fits the actual bottleneck.** The Investigate module's
  parallel fan-out (`asyncio.gather` across 5+ providers with per-provider
  timeouts) is a first-class use case for `async def`, not a bolted-on
  extension. Django's async support was still second-class at the time of
  writing; Flask has none without an extension.
- **Pydantic is the same library twice.** Request/response validation and
  LLM structured-output validation (`InvestigateReportOutput`,
  `AlertTriageOutput`, etc.) both use Pydantic v2 models. One mental model,
  one place to look when a schema doesn't match — including the AI
  router's own repair-prompt retry on a validation failure.
- **Auto-generated OpenAPI docs double as a free API showcase** — `/docs`
  is a legitimate portfolio artifact with zero extra work.
- **Less framework to fight.** Django's ORM and admin are strong but
  unused weight here; the project needed a thin, explicit layer over
  SQLAlchemy, not an opinionated full-stack framework.

## Consequences
- No Django admin — any admin tooling is hand-rolled (acceptable; none was
  needed).
- The team (one dev) owns more wiring (dependency injection via FastAPI's
  `Depends`, manual session-per-request lifecycle) that Django would
  provide out of the box. In exchange, the async engine, the repository →
  service → route layering, and the RBAC `require_permission` dependency
  factory are all straightforward to reason about and test.
- SQLAlchemy's async mode has real sharp edges (see the "Known gotchas"
  section of `docs/architecture.md` — event-loop-bound engines,
  `eager_defaults` for `onupdate`-generated columns) that a sync ORM
  wouldn't have surfaced. Worth it for the Investigate module's
  concurrency; would reconsider for a purely CRUD service with no
  external I/O fan-out.
