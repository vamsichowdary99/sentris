# ADR 0002: LiteLLM router with a free-first provider fallback chain

## Status
Accepted

## Context
Every AI feature (alert summary, triage, investigation steps, AI-based
MITRE mapping, batch prioritization, case incident reports, IOC
investigation reports, NL search) needs an LLM call. A portfolio project
can't assume the reviewer — or the author, indefinitely — has a paid API
key. At the same time, hand-writing a separate client per provider
(NVIDIA NIM, Groq, OpenRouter, Ollama) would mean four slightly-different
request/response shapes to maintain.

## Decision
Route every AI call through a single `AIRouter` (`app/ai/router.py`)
built on LiteLLM, which tries providers in priority order — NVIDIA NIM →
Groq → OpenRouter (free tier) → Ollama (local) — and falls back to the
next on any failure (missing key, timeout, rate limit, connection
refused). One retry per provider absorbs the class of near-instant,
misleading "Timeout" error observed live against Groq during manual
testing before falling through the chain.

## Rationale
- **One call site, one output contract.** Every task calls
  `router.complete(...)` and gets back a uniform `LLMResponse`
  (content/provider/model/tokens/latency). The provider actually used is
  recorded per-request and persisted in `ai_analyses.provider` /
  `.model`, so which free tier answered a given question is always
  auditable after the fact.
- **Zero-cost is a real constraint, not a stretch goal.** With no keys
  configured at all, every AI endpoint returns a clear
  `503 ai_unavailable` instead of a stack trace or a silent hang — the
  rest of the app (enrichment, MITRE mapping, search) is completely
  unaffected, matching the same "feature degrades, app doesn't" pattern
  used for the threat-intel providers (ADR 0003).
- **Structured-output validation lives next to the call, not the
  provider.** `app/ai/structured.py`'s `run_structured()` renders a
  versioned Jinja2 prompt, calls the router in JSON mode, validates the
  response against a Pydantic schema, and — this is the part a raw
  provider SDK doesn't give you — retries once with a repair prompt
  ("your previous response didn't match the schema") before giving up.
  Provider-agnostic by construction, since it only depends on
  `AIRouter.complete`.
- **Caching is provider-agnostic too.** Responses are cached in Redis by
  `hash(system + user + json_mode)`, so a repeated question (or a
  re-investigated indicator) doesn't re-spend a free-tier quota
  regardless of which provider answered it.

## Consequences
- LiteLLM is a fairly heavy dependency (it vendors SDK-adjacent code for
  many providers we don't use) in exchange for not hand-rolling four
  HTTP clients. Accepted the trade — the alternative was real
  duplication, not a lighter alternative with equivalent behavior.
- NVIDIA NIM is proxied through LiteLLM's generic `openai/<model>`
  provider with a custom `api_base`, rather than a
  version-specific `nvidia_nim` provider name, so the integration
  doesn't silently break across LiteLLM upgrades.
- Prompt-injection guardrails (`app/ai/guardrails.py`) are enforced at
  the call site — untrusted alert/case/IOC content is always wrapped in
  an explicit `<untrusted_data>` delimiter with role-marker tokens
  stripped — rather than trusted to any one provider's own safety
  behavior, since the fallback chain means the actual model answering a
  given request can vary.
