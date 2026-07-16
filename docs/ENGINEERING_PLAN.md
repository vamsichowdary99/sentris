# Sentris — AI-Powered SOC Analyst Platform (Engineering Plan)

## Context

This is a **greenfield, portfolio-flagship** project. The goal is a production-quality, AI-powered Security Operations Center (SOC) platform that makes recruiters in Paris (Security Engineer, Security Automation Engineer, AI Engineer, Platform Engineer) immediately think: *"this person understands software engineering, security, AI, and automation."*

**Locked decisions:**
- **Stack:** Python (FastAPI) backend + React/Next.js frontend.
- **AI:** **Free-first, provider-agnostic.** No paid API keys required. Routing layer over free LLM providers (NVIDIA NIM, Groq, Hugging Face, OpenRouter free tier, Ollama local).
- **Scope:** Impressive MVP that fully demos the core loop, then phased extensions.
- **Data:** Realistic replayable alert simulator (real Wazuh/Sysmon/Suricata sample data) + a documented connector to plug in live Wazuh.
- **Build location:** subfolder `c:\AI SOC PLATFORM\sentris`.
- **Project name:** confirmed **Sentris**.
- **Git:** `git init` locally now; push to a public GitHub repo **only after the project is finished**.
- **Environment:** Docker Desktop is installed and available.
- **Execution:** implemented using **Claude Sonnet** (see `SONNET_BUILD_PROMPT.md` in this folder).

**The flagship workflow this platform proves out:**
```
Alert arrives → AI summarizes → Threat-intel enrichment → MITRE ATT&CK mapping
→ AI-recommended investigation steps → Analyst reviews & creates a case → AI-generated incident report
```

---

## 1. Product Vision

### Product name — 10 candidates
| # | Name | Angle |
|---|------|-------|
| 1 | **Sentris** ⭐ | "sentry" + modern suffix; short, ownable, brandable, no major trademark clash |
| 2 | ThreatPilot | AI copilot for threats — descriptive |
| 3 | Argus AI | Hundred-eyed guardian of Greek myth; all-seeing monitoring |
| 4 | Aegis | Shield of Athena; classic security connotation |
| 5 | BlueSentinel | Blue-team SOC signal |
| 6 | Corvus | Raven — watchful, intelligent |
| 7 | Vigil AI | Vigilance / watch |
| 8 | Warden | Guardian / keeper |
| 9 | Nocturn | The SOC that watches at night |
| 10 | Halberd | Guard's weapon; sharp, defensive |

**Chosen: `Sentris`.** Rationale: short (7 letters), memorable, ownable (`.io`/`.dev` likely free, clean GitHub org), evokes *sentry/sentinel* without colliding with Microsoft Sentinel or Elastic. Tagline: **"Sentris — the AI SOC analyst copilot."**

### One-line pitch
> Sentris ingests security alerts, uses AI to summarize and triage them, enriches them with live threat intelligence, maps them to MITRE ATT&CK, recommends investigation steps, and lets analysts spin up a case and generate a full incident report — cutting alert triage from ~30 minutes to under 2.

### The problem it solves
SOC analysts drown in alerts (alert fatigue). Most tools **show** data; they don't **reason** over it. Analysts waste time context-switching between the SIEM, VirusTotal, AbuseIPDB, MITRE docs, and a ticketing system. Sentris collapses that loop into one AI-assisted surface.

### Why this is a strong portfolio piece
It sits at the intersection of **four hiring tracks at once** — security domain knowledge, AI/LLM engineering, backend/API design, and platform/automation — which is exactly the rare combination Paris SOC/Detection-Engineering teams (and AI-security startups) are hiring for.

---

## 2. Feature List (with *why each exists*)

### MVP (Phase-gated, ships first)
| Feature | What it does | Why it exists (recruiter signal) |
|---|---|---|
| **Auth + RBAC** | JWT login, roles: Admin / SOC Lead / Analyst / Viewer | Proves secure backend + access-control design |
| **Dashboard** | KPI tiles, alert volume, MTTR, severity breakdown, MITRE heatmap | Data viz + product sense |
| **Alert Management** | List, filter, sort, detail view, status workflow (New→Triaging→Closed) | Core CRUD + state machine design |
| **AI Alert Summary** | Plain-English summary + "what happened / why it matters" | The headline AI feature |
| **AI Triage & Severity** | AI estimates severity + priority + confidence | Shows structured LLM output + validation |
| **Threat-Intel Enrichment** | Auto-enrich IPs/hashes/domains via VirusTotal, AbuseIPDB, Shodan | Security automation + external API orchestration |
| **MITRE ATT&CK Mapping** | AI maps alert to tactics/techniques + explains them | Domain depth + reference-data modelling |
| **AI Investigation Steps** | AI generates next-best investigative actions | "Copilot" value prop |
| **Case / Incident Management** | Promote alerts → case, assign, comment, timeline | Workflow + collaboration |
| **AI Incident Report** | One-click narrative report (Markdown/PDF) from a case | Impressive demo finale |
| **IOC Management** | Track indicators, link to alerts/cases | Threat-intel data modelling |
| **Asset Inventory** | Hosts/users involved, criticality | Context for prioritization |
| **Threat Timeline** | Chronological event view per case | Investigation UX |
| **Search + NL Search** | Structured filters **and** natural-language ("failed logins yesterday") | RAG / text-to-query — big AI signal |
| **SOC Metrics** | MTTA, MTTR, alerts/analyst, false-positive rate | Observability / product analytics |
| **Notifications** | In-app + webhook (Slack/Discord/email) on new case | Automation + eventing |
| **Audit Logs** | Every sensitive action recorded | Security engineering rigor |
| **IOC Investigate / Analyzer** | Paste any IP/hash/domain/URL → auto-detect type → fan out to multiple threat-intel sources → AI-synthesized verdict + report | Interactive "try it yourself" showpiece; real SOC analyzer workflow (see §16) |

### Phase-2+ (extensions)
Playbook automation engine (SOAR-lite), live Wazuh/Splunk ingestion, Sigma-rule detection, semantic alert clustering (pgvector), multi-tenant orgs, analyst leaderboard/gamification, alert deduplication & correlation, scheduled AI digests, model-eval dashboard.

---

## 3. Technical Architecture

### Recommended stack
| Layer | Choice | Why |
|---|---|---|
| **Frontend** | Next.js 15 (App Router) + React + TypeScript + Tailwind + shadcn/ui | Modern, enterprise-grade, fast to build premium UI |
| **Charts** | Recharts (+ visx for the MITRE heatmap) | Clean, composable, themable |
| **Backend** | FastAPI (Python 3.12) | Async, typed, auto OpenAPI docs; security/AI ecosystem is Python-native |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic migrations | Industry standard, migration story |
| **Validation** | Pydantic v2 | Request/response + **LLM output schema validation** |
| **Database** | PostgreSQL 16 (+ `pg_trgm` for search, optional `pgvector` for semantic) | Normalized relational + full-text + vector in one |
| **Queue / Workers** | Celery + Redis (broker + cache) | Async enrichment & AI pipeline; classic SOAR pattern |
| **AI Router** | **LiteLLM** in front of free providers | Single OpenAI-compatible interface, fallbacks, cost/latency tracking |
| **Auth** | JWT (access + refresh), `passlib`/`argon2` hashing, `python-jose` | Standard, secure |
| **Auth (frontend)** | NextAuth or lightweight token store + middleware | Route protection |
| **Realtime** | WebSockets (FastAPI) / SSE for live alert feed | "Live SOC" feel |
| **Containerization** | Docker + docker-compose (one-command demo) | Platform-eng signal; reviewer runs `docker compose up` |
| **Deployment** | Compose for demo; documented path to Kubernetes (Helm) + Terraform | Cloud-ready story |
| **Logging** | `structlog` JSON logs + request IDs; optional OpenTelemetry | Observability |
| **Testing** | pytest + httpx + factory-boy (backend); Vitest + Playwright (frontend) | Test discipline |
| **CI/CD** | GitHub Actions: lint (ruff/mypy/eslint) → test → build → Trivy scan | DevSecOps signal |

### High-level component diagram
```
                        ┌───────────────────────────────┐
                        │  Next.js Frontend (SPA/SSR)  │
                        │  Dashboard · Alerts · Cases  │
                        └───────────┬────────────┘
                                        │ HTTPS / WS
                        ┌─────────────▼─────────────┐
                        │        FastAPI (API Layer)    │
                        │  Auth · RBAC · Rate-limit     │
                        └───────────┬────────────┘
             ┌──────────────────────┼───────────────────────┐
             ▼                          ▼                           ▼
   ┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
   │  Service Layer   │      │   AI Layer          │      │  Integration Layer │
   │ Alerts/Cases/IOC │◄────►│ LiteLLM router      │      │ VT·AbuseIPDB·Shodan│
   │ Repositories     │      │ prompts · validators│      │ Wazuh connector    │
   └────────┬───────┘      │ enrichment · report │      │ Sigma · MITRE ref  │
            │                └─────────┬────────┘      └─────────┬──────────┘
            ▼                          ▼                           ▼
   ┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
   │   PostgreSQL 16  │      │  Celery Workers     │◄────►│   Redis (broker)   │
   │  (+pg_trgm/vec)  │      │  async AI pipeline  │      │   + cache          │
   └────────────────┘      └─────────────────┘      └─────────────────────┘
            ▲
   ┌─────────────────┐
   │ Alert Simulator  │  replays real Wazuh/Sysmon/Suricata samples → ingest webhook
   └─────────────────┘
```

### The AI Layer (the differentiator) — free-first design
- **Router:** LiteLLM exposes one OpenAI-compatible call; config picks provider + fallback chain.
- **Fallback chain (all free):** `NVIDIA NIM (build.nvidia.com)` → `Groq` → `OpenRouter (free models)` → `Ollama (local, offline)`. Hugging Face Inference as an alternate.
  - Cloud demo default: **NVIDIA NIM** or **Groq** (fast, generous free tiers, hosts Llama 3.3 70B / Nemotron / Mistral).
  - Fully offline/dev default: **Ollama** (Llama 3.1 8B / Qwen2.5 / Mistral) — zero network, reviewers run it locally.
- **Structured outputs:** every AI task returns JSON validated by a Pydantic schema (severity, techniques[], confidence, steps[]). Invalid output → auto-retry with repair prompt.
- **Prompt management:** versioned prompt templates in `prompts/` (Jinja2), each tagged with a version stored alongside the AI result for reproducibility.
- **Guardrails:** input sanitization against prompt injection, token/size caps, PII scrubbing option, per-request timeout + graceful degradation (feature works without AI, just less rich).
- **Caching:** hash(prompt+model) → Redis cache to avoid re-billing free-tier limits and speed demos.
- **Eval harness (Phase-6/extension):** small golden dataset of alerts + expected fields → measure summary quality, MITRE-mapping accuracy, severity agreement. Big AI-Engineer signal.

### Natural-language search design
NL query → LLM converts to a **safe structured filter** (allow-listed fields/operators, never raw SQL) → executed via repository layer. Optional semantic layer: embed alerts with a free HF embedding model → `pgvector` similarity for "find alerts like this one."

---

## 4. Database Design (normalized PostgreSQL)

### Tables & key columns
| Table | Purpose | Key columns |
|---|---|---|
| `organizations` | Multi-tenant-ready root | id, name, created_at |
| `users` | Accounts | id, org_id→organizations, email(unique), password_hash, full_name, is_active, last_login_at |
| `roles` | RBAC roles | id, name (admin/soc_lead/analyst/viewer) |
| `permissions` | Fine-grained perms | id, code (e.g. `case.create`) |
| `role_permissions` | M:N | role_id, permission_id |
| `user_roles` | M:N | user_id, role_id |
| `refresh_tokens` | Session/rotation | id, user_id, token_hash, expires_at, revoked_at |
| `assets` | Hosts/users/services | id, org_id, hostname, ip, os, owner, criticality (enum), tags |
| `alerts` | Core alert | id, org_id, source (wazuh/sysmon/suricata…), external_id, title, raw (jsonb), severity (enum), ai_severity, priority, status (enum), rule_name, src_ip, dst_ip, host_asset_id→assets, user_subject, occurred_at, ingested_at, search_vector (tsvector), embedding (vector, nullable) |
| `alert_events` | Raw log lines behind an alert | id, alert_id, event_ts, payload (jsonb) |
| `iocs` | Indicators | id, org_id, type (ip/domain/hash/url), value(unique per org), reputation, first_seen, last_seen, source |
| `alert_iocs` | M:N | alert_id, ioc_id |
| `enrichments` | Threat-intel results | id, ioc_id, provider (virustotal/abuseipdb/shodan), verdict, score, raw (jsonb), fetched_at |
| `mitre_techniques` | ATT&CK reference (seeded) | id (T-code, PK), name, tactic, description, url |
| `alert_mitre` | M:N mapping | alert_id, technique_id, source (ai/rule), confidence |
| `cases` | Incident/case | id, org_id, title, summary, status (open/investigating/contained/closed), severity, assignee_id→users, created_by, opened_at, closed_at, search_vector |
| `case_alerts` | M:N | case_id, alert_id |
| `ai_analyses` | Stored AI outputs | id, entity_type (alert/case), entity_id, task (summary/triage/steps/report/mitre), model, provider, prompt_version, output (jsonb), tokens_in, tokens_out, latency_ms, created_at |
| `timeline_events` | Case timeline | id, case_id, ts, kind, actor_id, description, meta (jsonb) |
| `comments` | Notes on alerts/cases | id, entity_type, entity_id, user_id, body, created_at |
| `reports` | Generated incident reports | id, case_id, format, content (text), generated_by, created_at |
| `notifications` | In-app + outbound | id, user_id, type, payload (jsonb), read_at, created_at |
| `integrations` | Provider configs | id, org_id, kind, config (jsonb, secrets encrypted), enabled |
| `automation_runs` | Playbook executions (Phase-7) | id, trigger, playbook, status, steps (jsonb), started_at, finished_at |
| `saved_searches` | Reusable queries | id, user_id, name, query (jsonb) |
| `tags` / `taggables` | Free tagging | polymorphic |
| `audit_logs` | Security audit trail | id, org_id, user_id, action, entity_type, entity_id, ip, user_agent, meta (jsonb), created_at |

### Relationships (summary)
- `organizations` 1—N `users`, `alerts`, `cases`, `assets`, `iocs`.
- `alerts` N—M `cases` (via `case_alerts`), N—M `iocs`, N—M `mitre_techniques`.
- `cases` 1—N `timeline_events`, 1—N `reports`, N—1 assignee (`users`).
- `iocs` 1—N `enrichments`.
- `alerts`/`cases` 1—N `comments`, 1—N `ai_analyses`.

### Indexes
- FKs all indexed. Composite: `alerts(org_id, status, severity, occurred_at DESC)` for the main list.
- `alerts(occurred_at DESC)`, `cases(status, opened_at DESC)`.
- GIN on `alerts.search_vector`, `cases.search_vector` (full-text); `pg_trgm` GIN on `iocs.value`, `assets.hostname` (fuzzy).
- Unique: `users(email)`, `iocs(org_id, value)`, `enrichments(ioc_id, provider)`.
- Optional IVFFlat/HNSW on `alerts.embedding` (pgvector) for semantic search.

### DB permissions
- App connects as a least-privilege role (`sentris_app`: CRUD on app tables, no DDL).
- Migrations run as a separate `sentris_migrator` role.
- Secrets (integration API keys) encrypted at rest (app-level Fernet/`cryptography`), never plaintext in `integrations.config`.

---

## 5. Folder Structure

### Repository root
```
sentris/
├── README.md                  # hero image, demo GIF, quickstart, architecture
├── docker-compose.yml         # one-command full stack
├── docker-compose.dev.yml
├── .env.example               # documents free-provider keys (all optional)
├── Makefile                   # make up / make seed / make test / make demo
├── docs/                      # architecture, ADRs, API, screenshots
│   ├── architecture.md
│   ├── adr/
│   └── screenshots/
├── .github/workflows/         # ci.yml (lint→test→build→trivy)
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/              # config, security, logging, deps, rate-limit
│   │   ├── api/v1/            # routers: auth, alerts, cases, iocs, assets,
│   │   │                      #          ai, search, metrics, users, integrations
│   │   ├── services/          # business logic (alert, case, enrichment, metrics)
│   │   ├── repositories/      # DB access (SQLAlchemy)
│   │   ├── models/            # ORM models
│   │   ├── schemas/           # Pydantic request/response + AI output schemas
│   │   ├── ai/                # llm_router, prompts/, validators, tasks, eval/
│   │   ├── integrations/      # virustotal, abuseipdb, shodan, wazuh, mitre
│   │   ├── workers/           # celery app + tasks (pipeline)
│   │   └── db/                # session, base, seeds
│   ├── alembic/               # migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── app/                   # Next.js App Router (dashboard, alerts, cases…)
│   ├── components/            # ui/ (shadcn), charts/, alerts/, cases/, ai/
│   ├── lib/                   # api client, auth, hooks, utils
│   ├── stores/                # state (zustand/react-query)
│   └── package.json
├── simulator/                 # alert generator/replayer + sample datasets
│   ├── datasets/              # real Wazuh/Sysmon/Suricata samples
│   └── replay.py
└── infra/                     # k8s helm charts, terraform (Phase-8+)
```

---

## 6. API Specification (REST, `/api/v1`)

**Conventions:** JSON; JWT `Authorization: Bearer`; cursor/offset pagination (`?page&size`); filtering via query params; consistent error envelope `{ "error": { "code", "message", "details" } }`; every mutation writes an `audit_log`.

### Auth
| Method | Path | Body → Response |
|---|---|---|
| POST | `/auth/register` | `{email,password,full_name}` → `201 {user}` (admin-gated in prod) |
| POST | `/auth/login` | `{email,password}` → `{access_token, refresh_token, user}` |
| POST | `/auth/refresh` | `{refresh_token}` → `{access_token}` |
| POST | `/auth/logout` | revokes refresh token → `204` |
| GET | `/auth/me` | → current user + roles/perms |

### Alerts
| Method | Path | Notes |
|---|---|---|
| GET | `/alerts` | filters: `status,severity,source,src_ip,from,to,q,mitre` + pagination |
| POST | `/alerts` | ingest one alert (used by simulator/Wazuh webhook) → triggers pipeline |
| POST | `/alerts/bulk` | batch ingest |
| GET | `/alerts/{id}` | full detail + iocs + mitre + ai_analyses + enrichments |
| PATCH | `/alerts/{id}` | update status/severity/assignment |
| POST | `/alerts/{id}/enrich` | force threat-intel enrichment |
| GET | `/alerts/{id}/events` | raw underlying events |

### AI
| Method | Path | Purpose |
|---|---|---|
| POST | `/ai/alerts/{id}/summarize` | plain-English summary |
| POST | `/ai/alerts/{id}/triage` | severity + priority + confidence (validated JSON) |
| POST | `/ai/alerts/{id}/investigate` | recommended investigation steps |
| POST | `/ai/alerts/{id}/mitre` | map + explain ATT&CK techniques |
| POST | `/ai/alerts/summarize-batch` | summarize/prioritize many alerts |
| POST | `/ai/cases/{id}/report` | generate incident report |
| POST | `/ai/mitre/{technique}/explain` | explain a technique in plain English |
| POST | `/ai/iocs/{id}/summary` | summarize IOC reputation |
| POST | `/ai/search` | NL → structured query → results ("failed logins yesterday") |

### Investigate / IOC Analyzer (see §16)
| Method | Path | Purpose |
|---|---|---|
| POST | `/investigate` | `{indicator}` → auto-detect type → multi-source enrichment → normalized result |
| POST | `/investigate/report` | `{indicator}` or `{ioc_id}` → AI-synthesized report across all sources |
| GET | `/investigate/{ioc_id}` | cached multi-source result + linked alerts/cases |
| POST | `/investigate/{ioc_id}/refresh` | force-refresh a specific/all providers (bypass cache) |

### Cases / IOCs / Assets / MITRE / Metrics / Search / Users / Notifications / Integrations
| Method | Path |
|---|---|
| GET/POST/GET{id}/PATCH | `/cases`, `/cases/{id}` (+ `/cases/{id}/alerts`, `/timeline`, `/comments`, `/report`) |
| GET/POST/GET{id} | `/iocs`, `/iocs/{id}` (+ `/enrich`) |
| GET/POST/GET{id} | `/assets`, `/assets/{id}` |
| GET | `/mitre/techniques`, `/mitre/techniques/{id}` |
| GET | `/metrics/overview`, `/metrics/mttr`, `/metrics/mitre-heatmap`, `/metrics/analyst` |
| GET/POST | `/search`, `/search/saved` |
| GET/POST/PATCH/DELETE | `/users`, `/users/{id}` (admin) |
| GET/PATCH | `/notifications`, `/notifications/{id}/read` |
| GET/POST/PATCH | `/integrations` (admin) |
| GET | `/audit-logs` (admin/soc_lead) |
| WS | `/ws/alerts` (live feed) |

**Auto docs:** FastAPI serves OpenAPI/Swagger at `/docs` — free interactive API showcase for recruiters.

---

## 7. Security Design
- **JWT:** short-lived access (15 min) + rotating refresh tokens (hashed in DB, revocable).
- **Password hashing:** Argon2id via passlib.
- **RBAC:** permission-based dependency guards on every route (`require("case.create")`).
- **Rate limiting:** per-IP + per-user (SlowAPI/Redis) on auth + AI endpoints.
- **Input validation:** Pydantic everywhere; reject unknown fields.
- **Prompt-injection defense:** treat all alert content as untrusted; delimit + instruct; allow-list NL-search fields; never build SQL from LLM output.
- **Secrets:** `.env` for dev, encrypted `integrations.config`, never logged; secret scanning in CI.
- **Secure headers:** CSP, HSTS, X-Content-Type-Options, X-Frame-Options via middleware.
- **CSRF:** SameSite cookies where cookies used; bearer tokens for API.
- **Audit logs:** immutable append of sensitive actions with actor/IP/UA.
- **Container hardening:** non-root images, pinned deps, Trivy scan in CI.
- **CORS:** strict allow-list.

---

## 8. Development Roadmap & Time Estimates
*(Assumes ~part-time solo pace; ranges given. "Impressive MVP first" = Phases 1–6.)*

| Phase | Scope | Deliverable | Est. |
|---|---|---|---|
| **1. Architecture & Setup** | Repo, docker-compose, Postgres+Redis, CI skeleton, ADRs, schema + Alembic init, MITRE seed | `docker compose up` boots empty app + `/docs` | **3–5 days** |
| **2. Backend Core** | Models, repositories, services, alert/case/IOC/asset CRUD, search, metrics endpoints, seed data | Full REST API green in Swagger + tests | **1–1.5 weeks** |
| **3. Frontend Shell** | Next.js app, layout, auth screens, dashboard, alert list+detail, case views, charts | Clickable UI wired to API | **1.5–2 weeks** |
| **4. Auth & RBAC** | JWT, refresh rotation, roles/permissions, guards, audit logs, protected routes | Login + role-gated access working end-to-end | **4–6 days** |
| **5. Alert Pipeline** | Simulator + sample datasets, ingest webhook, Celery pipeline, threat-intel enrichment, MITRE mapping | Live alerts flow in and enrich automatically | **1–1.5 weeks** |
| **6. AI Features** | LiteLLM router + free providers, prompts, validators, summarize/triage/investigate/report/NL-search, caching | Full AI copilot loop demoable | **1.5–2 weeks** |
| **— MVP COMPLETE —** | | **Flagship demo ready** | **~6–8 weeks** |
| **7. Automation (SOAR-lite)** | Playbook engine, notifications (Slack/Discord/email), auto-case rules | Alert→AI→case→notify with no human step | **1–1.5 weeks** |
| **8. Deployment & Polish** | Helm/K8s manifests, Terraform sample, OpenTelemetry, load test, demo video, docs, screenshots | Cloud-ready + polished portfolio artifact | **1–1.5 weeks** |

---

## 9. Sprint Planning (2-week sprints)
- **Sprint 1 — Foundation:** Phase 1 + start Phase 2 (auth models, alert model, migrations, seed, CRUD for alerts).
- **Sprint 2 — API + Shell:** finish Phase 2, start Phase 3 (dashboard + alert list/detail).
- **Sprint 3 — App usable:** finish Phase 3 + Phase 4 (auth/RBAC end-to-end, cases UI).
- **Sprint 4 — Data flows:** Phase 5 (simulator, pipeline, enrichment, MITRE mapping).
- **Sprint 5 — Intelligence:** Phase 6 (AI router + all AI endpoints + NL search + caching).
- **Sprint 6 — Automation & Ship:** Phases 7–8 (playbooks, notifications, deploy, demo video, README polish).

Each sprint ends with: passing CI, an updated demo GIF, and a tagged release.

---

## 10. Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Free LLM rate limits / downtime mid-demo | Fallback chain + Redis response cache + Ollama local default for offline demos |
| LLM returns malformed/hallucinated output | Pydantic-validated JSON, repair-retry, confidence scores, "AI-assisted, verify" UI labeling |
| Scope creep (never ships) | Hard MVP gate at Phase 6; extensions clearly deferred |
| Threat-intel API free-tier limits (VT/AbuseIPDB) | Cache enrichments in DB, rate-limit, mock provider for demo mode |
| Prompt injection via alert content | Untrusted-content handling, allow-listed NL-search, no LLM→SQL |
| Solo bandwidth | Ship vertically slice-by-slice; keep each phase independently demoable |
| Secrets leakage in a public repo | `.env.example` only, secret scanning in CI, encrypted integration config |
| Realistic-looking but fake data misread as real | Clearly label demo/simulated data in UI + README |

---

## 11. Future Enhancements
Semantic alert clustering & dedup (pgvector), full SOAR playbook designer, live Splunk/Elastic ingestion, Sigma-rule engine, YARA scanning, model-eval dashboard with quality metrics, agentic multi-step investigation (tool-calling AI that queries the DB itself), multi-tenant SaaS mode, SSO/OIDC, mobile view, analyst gamification/leaderboard, threat-hunting notebooks, scheduled AI briefings.

---

## 12. Resume Impact
**Bullet examples:**
- *"Built Sentris, an AI-powered SOC platform (FastAPI, PostgreSQL, Celery, Next.js) that ingests security alerts, auto-enriches them with threat intel, maps them to MITRE ATT&CK, and uses LLMs to summarize, triage, and recommend investigation steps — cutting simulated triage time ~90%."*
- *"Designed a provider-agnostic AI layer (LiteLLM) over free LLM providers with schema-validated outputs, prompt versioning, caching, and a fallback chain — zero API cost."*
- *"Implemented JWT auth with rotating refresh tokens, permission-based RBAC, audit logging, rate limiting, and Trivy-scanned Docker images in a GitHub Actions pipeline."*
- *"Built an async alert-enrichment pipeline (Celery/Redis) integrating VirusTotal, AbuseIPDB, and Shodan with response caching."*

**Signals demonstrated:** secure API design, LLM/AI engineering with guardrails, security automation/SOAR, threat-intel integration, MITRE ATT&CK fluency, containerization, CI/DevSecOps, data modelling, modern frontend.

---

## 13. Portfolio Screenshots to Create
1. **Dashboard** — KPI tiles + alert-volume chart + severity donut + **MITRE ATT&CK heatmap**.
2. **Alert detail with AI summary** panel (the hero shot).
3. **AI triage** card — severity/priority/confidence with reasoning.
4. **Threat-intel enrichment** — VT/AbuseIPDB/Shodan verdicts on an IOC.
5. **MITRE mapping** — techniques highlighted + AI explanation.
6. **AI investigation steps** checklist.
7. **Case view** with timeline.
8. **AI-generated incident report** (Markdown/PDF).
9. **Natural-language search** — query + structured results.
10. **Swagger `/docs`** — full API surface.
11. **Architecture diagram** (from `docs/`).
12. **Terminal:** `docker compose up` → running stack.

Capture in **both light and dark themes**; put the top 3 + a 30–60s demo GIF at the top of the README.

---

## 14. Demo Scenarios (script for recruiters)
1. **The core loop (headline):** Simulator fires a "brute-force → successful login → suspicious process" alert → it appears live on the dashboard → open it → AI summary explains it in plain English → enrichment flags the source IP as malicious → MITRE shows T1110/T1078 → AI lists investigation steps → promote to a case → click **Generate Report** → polished incident report appears.
2. **Alert-fatigue triage:** 50 alerts in the queue → "AI prioritize" → top-5 critical surfaced with reasoning.
3. **Natural-language search:** type *"show failed logins from yesterday over 5 attempts"* → structured results.
4. **Automation (Phase-7):** new critical alert auto-creates a case and pings a Slack/Discord webhook — no human click.
5. **Provider swap:** flip config from NVIDIA NIM → local Ollama; same features, offline, $0.

---

## 15. GitHub Repository Structure
- **Public repo `sentris`** (see §5 layout).
- **README:** hero banner, demo GIF, one-command quickstart (`docker compose up` + `make seed`), architecture diagram, feature matrix, tech-stack badges, screenshots, "why I built this" + roadmap. This is the single most-viewed artifact — invest in it.
- **`docs/adr/`:** Architecture Decision Records (why FastAPI, why LiteLLM, why free providers) — shows senior judgment.
- **CI badge**, license (MIT), `CONTRIBUTING.md`, issue/PR templates.
- **Conventional commits + tagged releases** (v0.1 per sprint) — shows disciplined delivery.
- **`.env.example`** documenting every (optional) free provider key.
- Pin a **release with the demo video**; optionally a live demo link (Fly.io/Render free tier) using Ollama or a free provider.

---

## 16. IOC Investigate & Multi-Source Enrichment Module (post-Phase-6)

**Goal:** an interactive "Investigate" workbench where an analyst pastes **any indicator** (IP, domain, URL, or file hash), the platform **auto-detects the type**, fans out to multiple threat-intel sources **in parallel**, normalizes the results, and the AI produces a synthesized verdict + full report. This is the flagship *"try it yourself"* moment for recruiters and a textbook SOC analyzer workflow.

**Design principle — reuse, don't rebuild:** this sits on top of the existing Phase-5 enrichment engine, the `iocs` + `enrichments` tables, the Redis cache, and the Phase-6 AI report generator. It is a **new entry point** into machinery that already exists, plus additional providers. A pasted indicator becomes a first-class `iocs` row, so the analyst can pivot to *"alerts touching this IOC,"* attach it to a case, and tag it.

### Provider stack (free-first) — what each source adds
| Source | IOC types | Unique value it adds to the report | Key? |
|---|---|---|---|
| **VirusTotal** | ip, domain, url, hash | Multi-engine verdict (the anchor) | Free key |
| **AbuseIPDB** | ip | Abuse-report confidence score | Free key |
| **Shodan** | ip | Open ports / services / exposed CVEs | Free key |
| **AlienVault OTX** ⭐ | all | **Attribution** — campaigns, threat actors, "pulses" | Free key |
| **GreyNoise (Community)** ⭐ | ip | "Benign internet-wide scanner vs targeted" — kills false positives | Free key |
| **abuse.ch (ThreatFox / MalwareBazaar / URLhaus)** | hash, domain, url | **Malware-family attribution** (e.g. hash → Emotet) | Free (auth key) |
| **urlscan.io** | domain, url | Screenshot + page resources + redirect chain | Free key |
| **WHOIS / RDAP** | domain | **Domain age** (newly-registered = strong phishing signal) | No key |
| Hybrid Analysis *(optional)* | hash | Sandbox behavioral report | Free tier |
| IPinfo / ipapi *(optional)* | ip | Clean geo + ASN/org for the report header | Free tier |

### IOC-type → provider routing
| Type | Providers queried |
|---|---|
| **IP** | VirusTotal · AbuseIPDB · Shodan · GreyNoise · AlienVault OTX (+ IPinfo geo) |
| **Domain** | VirusTotal · urlscan.io · AlienVault OTX · WHOIS/RDAP (age) |
| **URL** | VirusTotal · urlscan.io · AlienVault OTX |
| **Hash** | VirusTotal · abuse.ch (MalwareBazaar/ThreatFox) · AlienVault OTX (+ Hybrid Analysis) |

### Flow
```
Paste indicator → detect type (regex/validators; reject junk gracefully)
   → parallel fan-out to routed providers (asyncio.gather / Celery group), per-provider timeout
   → normalize each response into a common EnrichmentResult schema
   → upsert iocs row + one enrichments row per (ioc, provider), with fetched_at
   → AI synthesis over ALL sources → structured report
   → render: verdict badge · per-source cards · AI narrative · recommended actions · pivots
```

### Report structure the AI must produce (validated JSON → rendered + Markdown/PDF)
1. **Verdict** — malicious / suspicious / benign / unknown + **confidence** + one-line rationale.
2. **Attribution** — associated malware family / campaign / threat actor (from OTX + abuse.ch), or "none found."
3. **Evidence** — key findings per source (VT detections, abuse reports, open ports/CVEs, urlscan screenshot ref, domain age).
4. **Context** — geo/ASN, first/last seen, scanner-vs-targeted (GreyNoise), exposure (Shodan).
5. **Conflicts** — explicitly surface source disagreement (e.g. *"VT flags malicious; GreyNoise classifies as a benign mass-scanner — likely low-priority"*). **Do not average conflicting signals — reconcile and explain.**
6. **Recommended actions** — block/monitor/hunt steps, tailored to the indicator type.
7. **Related** — linked alerts/cases/assets already in Sentris that touch this IOC.

### Rules that make it look senior
- **Conflict reconciliation** (point 5) is the single biggest quality signal — instruct the prompt to weigh GreyNoise/benign context against raw VT counts rather than summing verdicts.
- **Cache per (ioc, provider) with timestamps.** Free tiers are rate-limited (VirusTotal ~4 req/min). Show *"cached 2h ago · re-run?"* in the UI — a feature, not a limitation. `/investigate/{ioc_id}/refresh` bypasses cache.
- **Graceful degradation** — a clean *"no data / not found"* from a source is a valid, displayed result; one provider timing out never fails the whole investigation.
- **Provider abstraction** — each source implements a common `ThreatIntelProvider` interface (`supports(type)`, `enrich(indicator) -> EnrichmentResult`) with a **mock provider** so the feature works with zero keys; real keys are opt-in per provider via `integrations`/`.env`.
- **Rate-limit + secret hygiene** — reuse existing SlowAPI limits; keys only in `.env`/encrypted `integrations.config`, never logged or committed.

### Screenshots to add (append to §13)
13. **Investigate page** — paste box + auto-detected type.
14. **Multi-source result** — per-source cards (VT/OTX/GreyNoise/Shodan) side by side.
15. **AI investigation report** — verdict + attribution + conflict callout + recommended actions.

### Where it fits
Build as **Phase 6.5** (now, since Phases 1–6 are complete): it depends on the Phase-5 enrichment engine and Phase-6 AI report generator, both of which already exist. Est. **4–6 days** (most sources are thin API wrappers over the existing enrichment abstraction).

---

## Verification (how we'll prove it works, later during build)
- `docker compose up` boots API + DB + Redis + workers + frontend; `/docs` and dashboard load.
- `make seed` loads MITRE reference + sample alerts; `python simulator/replay.py` streams alerts and they appear live.
- End-to-end pipeline test: ingest a sample alert → assert enrichment rows + MITRE mapping + `ai_analyses` summary created.
- AI-layer test: mock/record a free-provider response; assert validated schema; verify fallback triggers when primary fails.
- Auth/RBAC tests: analyst blocked from admin routes; audit-log row written on mutations.
- CI green (ruff/mypy/eslint + pytest + Vitest + Trivy).
- Manual demo run-through of all 5 scenarios in §14.
- **Investigate module (§16):** paste a known-bad IP → assert parallel enrichment rows from ≥3 providers, cache hit on re-run, AI report includes verdict + attribution + conflict handling; paste junk → graceful "invalid indicator"; one provider forced to time out → investigation still completes with partial results.

---

**Next step:** open a Claude Sonnet session in `c:\AI SOC PLATFORM` and paste the prompt from `SONNET_BUILD_PROMPT.md` to scaffold **Phase 1** (repo layout, docker-compose, Postgres+Redis, schema + Alembic init, MITRE seed, CI skeleton, README shell).
