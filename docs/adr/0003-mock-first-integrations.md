# ADR 0003: Every external integration ships mock-first, real-second

## Status
Accepted

## Context
Sentris depends on eight external threat-intel sources (VirusTotal,
AbuseIPDB, Shodan, AlienVault OTX, GreyNoise, abuse.ch, urlscan.io,
WHOIS/RDAP) plus the LLM layer (ADR 0002). All but WHOIS require a free
account and a key. A reviewer cloning the repo shouldn't have to sign up
for eight services before `docker compose up` shows something real, and
the project itself needed to keep developing against these integrations
before any key existed.

## Decision
Every `ThreatIntelProvider` has two implementations behind the same
interface (`check(ioc_type, value) -> EnrichmentResult`): a real one that
calls the actual API, and a deterministic mock that returns
realistically-shaped data. Selection is **per-provider, key-presence
only** — `app/integrations/investigate_registry.py`'s `_pick()` uses the
real client if that provider's specific key is configured, otherwise
falls back to its own mock. One key does not force any other provider
live, and a provider without a key never silently no-ops.

## Rationale
- **The mock isn't a placeholder, it's a fixture.** `mock_provider.py`'s
  `_classify()` derives a deterministic verdict from a hash of the IOC
  value, with a curated set of known-bad indicators reused across the
  bundled alert simulator, the AI attribution demo (one hash/domain
  pair resolves to a named "Emotet / SilentTrinity / APT-Ghost" story),
  and — deliberately — one IP where the mock GreyNoise classifies it a
  benign mass-scanner while every other mock provider calls it
  malicious, so the AI report's conflict-reconciliation logic has a
  guaranteed case to demonstrate on without needing a live network call.
- **Real-world API responses drift from what you'd guess.** Building the
  real providers against actual current docs (not assumptions) surfaced
  a concrete example: AlienVault OTX's `malware_families` is a list of
  *objects* (`{"display_name", "id", "target"}`), not plain strings —
  the kind of schema detail a "mock-shaped" real client would have
  gotten wrong silently. Each real provider is tested against fixtures
  shaped to the verified live schema, not the mock's shape.
- **Free-tier failure modes are handled as data, not exceptions.** A 404
  from VirusTotal/OTX/GreyNoise means "no data on this indicator" — a
  valid, displayed result — not an error. A 401/403 is classified
  `misconfigured` (bad key) and a 429 is `rate_limited` (with
  `Retry-After` respected and an escalating cooldown if it recurs),
  each surfaced distinctly in the UI rather than collapsed into one
  generic failure state. One provider being down, throttled, or
  misconfigured never fails the rest of an investigation — fan-out is
  `asyncio.gather` across independently-caught outcomes.
- **A client-side token bucket exists because reacting to 429 isn't
  enough.** VirusTotal's free tier is ~4 requests/minute; a Redis-backed
  bucket throttles proactively per provider so the app rarely produces
  the 429 in the first place, rather than only handling it after the
  fact.

## Consequences
- Two code paths per provider is real surface area (16 provider classes
  for 8 sources). Justified by the alternative: without a working mock,
  the Investigate module — arguably the project's best "try it
  yourself" moment — would show nothing at all to anyone who hasn't
  configured 7 free accounts first.
- The mock's curated known-bad values are a form of test data baked into
  production code (`mock_provider.py`). Acceptable here because the
  entire platform's alert data is explicitly simulated/demo data (see
  the README's data-provenance note) — there's no real-incident
  confidentiality boundary being crossed.
- WHOIS/RDAP always attempts the real lookup regardless of mock mode —
  it needs no key and no rate-limit budget to protect, so mocking it
  would only ever reduce fidelity for no benefit.
