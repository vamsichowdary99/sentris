# Sentris

**The AI SOC analyst copilot.**

[![CI](https://github.com/vamsichowdary99/sentris/actions/workflows/ci.yml/badge.svg)](https://github.com/vamsichowdary99/sentris/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Sentris ingests security alerts, uses AI to summarize and triage them,
enriches every indicator against real threat intelligence, maps activity
to MITRE ATT&CK, recommends investigation steps, and lets an analyst spin
up a case and generate a full incident report — all from alerts a
replayable simulator streams in, so the whole loop is demoable with one
command and zero paid API keys.

> **Data provenance:** every alert in this repo is **simulated/demo
> data** replayed by the bundled simulator — nothing here represents a
> real security incident. The **Investigate** module, however, calls
> real live threat-intel APIs (VirusTotal, AbuseIPDB, AlienVault OTX,
> urlscan.io) when you supply free keys, so indicators you paste in
> yourself get genuine, current answers.

![Sentris demo](docs/screenshots/demo.gif)

## What it actually does

1. A replayed alert lands → a Celery worker enriches its indicators and
   maps it to MITRE ATT&CK automatically.
2. An analyst opens it and asks the AI Copilot to **summarize**,
   **triage**, **investigate**, or **map MITRE techniques** — each a real
   LLM call, validated against a Pydantic schema, with a repair-retry if
   the model's JSON doesn't match.
3. **Investigate**: paste *any* IP, domain, URL, or file hash. Sentris
   detects the type, fans out in parallel to up to 5 threat-intel sources,
   and asks the AI to synthesize one verdict — including calling out when
   sources disagree instead of averaging them away (*"VirusTotal flags
   this malicious, but GreyNoise says it's a benign mass-scanner —
   likely low priority, not a targeted threat"*).
4. Promote to a **case**, click **Generate report**, get a full Markdown
   incident report grounded in that case's actual alerts and timeline.
5. Ask the alerts list a question in plain English — *"critical alerts
   from wazuh in the last day"* — and get back the exact filtered results,
   compiled through an allow-listed field schema, never raw SQL.

## Screenshots

| | |
|---|---|
| ![Dashboard](docs/screenshots/02-dashboard.png) | ![Alert detail + AI Copilot](docs/screenshots/04-alert-detail-ai-copilot.png) |
| Dashboard — live severity mix + ATT&CK coverage | Alert detail — AI summary/triage/investigation steps + MITRE mapping |
| ![Investigate — multi-source](docs/screenshots/05-investigate-multi-source.png) | ![Investigate — AI report](docs/screenshots/06-investigate-ai-report-conflict.png) |
| Investigate — 5 live sources in parallel, a real cross-source conflict | AI report reconciling that conflict, with attribution + recommended actions |
| ![Cases](docs/screenshots/07-cases-list.png) | ![Case report](docs/screenshots/08-case-detail-report.png) |
| Case queue | One-click AI incident report grounded in the case's real data |

## Stack

FastAPI (async) · PostgreSQL 16 · Celery + Redis · Next.js 15 · TypeScript
· Tailwind · LiteLLM (free-first AI router: NVIDIA NIM → Groq →
OpenRouter → Ollama) · Docker Compose

## Quickstart

```bash
cp .env.example .env
docker compose up --build
make migrate
make seed        # MITRE ATT&CK reference data
make seed-rbac   # roles/permissions
make seed-demo   # demo org + user + sample alerts/case
```

- Frontend: http://localhost:3000 (login `demo@sentris.io` / `demo12345`)
- API + Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health/ready

Stream a live-looking alert feed through the pipeline:

```bash
make demo         # one scenario
make demo-all     # all 5 bundled attack scenarios, once through
make demo-loop     # all scenarios, looping, 3x speed
```

Everything above runs with **zero API keys** — threat-intel and AI both
fall back to deterministic mock providers. To light up real data, add any
of the free-tier keys documented in `.env.example` (Groq and AlienVault
OTX are the fastest to sign up for) and recreate the containers so they
pick up the new env:

```bash
docker compose up -d --force-recreate api worker
```

## Why this exists

Most SOC tooling shows data; it doesn't reason over it. Analysts burn
time context-switching between the SIEM, VirusTotal, AbuseIPDB, MITRE
docs, and a ticketing system. Sentris collapses that loop: alert arrives
→ AI summarizes → threat-intel enrichment → MITRE ATT&CK mapping →
AI-recommended investigation steps → analyst creates a case → AI-generated
incident report — and adds an on-demand deep-dive (**Investigate**) for
any indicator an analyst wants to check by hand.

Full product rationale, database design, and API surface live in
[`docs/ENGINEERING_PLAN.md`](docs/ENGINEERING_PLAN.md). The reasoning
behind the major technical decisions — why FastAPI, why LiteLLM,
why every integration is mock-first, why the frontend is built the way
it is — lives in [`docs/adr/`](docs/adr/).

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the component
diagram and request lifecycle (alert ingest → enrichment → AI report).

```
Next.js frontend  →  FastAPI API  →  PostgreSQL
                          │
                          ├─ Celery workers ← Redis (broker + cache + rate limiter)
                          │      │
                          │      ├─ AI layer (LiteLLM router, 4-provider fallback)
                          │      └─ Integration layer (8 threat-intel sources,
                          │         each real-or-mock per configured key)
                          │
                     Alert simulator (replays sample Wazuh/Sysmon/Suricata data)
```

## Zero-cost by design, real data on demand

Every AI provider in the fallback chain (NVIDIA NIM → Groq → OpenRouter
free tier → Ollama local) and every threat-intel provider (VirusTotal,
AbuseIPDB, Shodan, AlienVault OTX, GreyNoise, abuse.ch, urlscan.io,
WHOIS/RDAP) has a free tier, runs fully offline, or needs no key at all.
`.env.example` documents every optional key — none are required for the
full demo to work.

Provider selection is **per-provider, not all-or-nothing**: add a
VirusTotal key and only VirusTotal goes live, every other source keeps
working on its mock. Real providers get proper free-tier citizenship —
a Redis-backed token bucket throttles VirusTotal to its documented
~4 requests/minute *before* it would 429, a 404 is treated as a valid
"no data" result rather than an error, and one source timing out or
being misconfigured never blocks the rest of an investigation.

## Development

```bash
make up                          # docker compose up --build
make logs                        # tail all service logs
make test                        # backend pytest suite
make lint                        # ruff + mypy
make revision m="add foo table"  # new Alembic migration
```

Frontend checks run inside its container:

```bash
docker compose exec frontend npx tsc --noEmit
docker compose exec frontend npm run lint
```

## Roadmap

- [x] Phases 1–6: scaffolding, backend core, frontend shell, auth/RBAC,
      alert pipeline, AI features
- [x] Phase 6.5: Investigate module, real threat-intel providers
- [x] Phase 8 (docs pass): README, screenshots, demo GIF, ADRs
- [ ] Phase 7: automation — auto-case-creation + Slack/Discord
      notification on critical alerts (deferred; low visual payoff for a
      portfolio relative to effort — see `docs/adr/` if this changes)
- [ ] Phase 8 (remaining): Kubernetes/Helm + Terraform samples,
      OpenTelemetry tracing, a load test

## License

MIT — see [`LICENSE`](LICENSE).
