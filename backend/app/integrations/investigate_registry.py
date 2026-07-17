from app.core.config import get_settings
from app.integrations.abusech import AbuseChProvider
from app.integrations.abuseipdb import AbuseIPDBProvider
from app.integrations.base import ThreatIntelProvider
from app.integrations.greynoise import GreyNoiseProvider
from app.integrations.mock_provider import (
    MockAbuseChProvider,
    MockAbuseIPDBProvider,
    MockGreyNoiseProvider,
    MockOTXProvider,
    MockShodanProvider,
    MockUrlscanProvider,
    MockVirusTotalProvider,
    MockWhoisProvider,
)
from app.integrations.otx import OTXProvider
from app.integrations.provider_health import get_provider_health
from app.integrations.shodan import ShodanProvider
from app.integrations.urlscan import UrlscanProvider
from app.integrations.virustotal import VirusTotalProvider
from app.integrations.whois import WhoisProvider
from app.models.enums import IOCType
from app.schemas.integrations import IntegrationStatusRead


def _pick(
    key: str | None, real: ThreatIntelProvider, mock: ThreatIntelProvider
) -> ThreatIntelProvider:
    """Per-provider opt-in: a key configured for THIS provider uses the
    real source; otherwise it falls back to its own mock. Independent of
    any global toggle — one key doesn't force every other provider live,
    and a provider without a key never silently no-ops."""
    return real if key else mock


def _all_investigate_providers() -> list[ThreatIntelProvider]:
    settings = get_settings()
    return [
        _pick(
            settings.virustotal_api_key,
            VirusTotalProvider(settings.virustotal_api_key or ""),
            MockVirusTotalProvider(),
        ),
        _pick(
            settings.abuseipdb_api_key,
            AbuseIPDBProvider(settings.abuseipdb_api_key or ""),
            MockAbuseIPDBProvider(),
        ),
        _pick(
            settings.shodan_api_key,
            ShodanProvider(settings.shodan_api_key or ""),
            MockShodanProvider(),
        ),
        _pick(
            settings.otx_api_key,
            OTXProvider(settings.otx_api_key or ""),
            MockOTXProvider(),
        ),
        _pick(
            settings.greynoise_api_key,
            GreyNoiseProvider(settings.greynoise_api_key or ""),
            MockGreyNoiseProvider(),
        ),
        _pick(
            settings.abusech_api_key,
            AbuseChProvider(settings.abusech_api_key or ""),
            MockAbuseChProvider(),
        ),
        _pick(
            settings.urlscan_api_key,
            UrlscanProvider(settings.urlscan_api_key or ""),
            MockUrlscanProvider(),
        ),
        # WHOIS/RDAP needs no key — always real (no rate-limit/cost reason
        # to mock it; network failure already degrades to "unknown").
        _pick("no-key-needed", WhoisProvider(), MockWhoisProvider()),
    ]


# Deliberately richer than the Phase-5 automatic per-alert enrichment
# (VT + AbuseIPDB only) — the Investigate module is the analyst-triggered
# deep-dive path, so it's fine for it to fan out to more (rate-limited)
# sources than the always-on ingestion pipeline does.
_ROUTING: dict[IOCType, frozenset[str]] = {
    IOCType.ip: frozenset({"virustotal", "abuseipdb", "shodan", "greynoise", "otx"}),
    IOCType.domain: frozenset({"virustotal", "urlscan", "otx", "whois"}),
    IOCType.url: frozenset({"virustotal", "urlscan", "otx"}),
    IOCType.hash: frozenset({"virustotal", "abusech", "otx"}),
}


def get_investigate_providers(ioc_type: IOCType) -> list[ThreatIntelProvider]:
    allowed = _ROUTING[ioc_type]
    return [
        p
        for p in _all_investigate_providers()
        if p.name in allowed and ioc_type in p.supported_types
    ]


async def list_provider_statuses() -> list[IntegrationStatusRead]:
    """Powers GET /integrations/status — for each provider, whether a key
    is configured, whether it's currently running live or mocked, and its
    last observed outcome (ok/misconfigured/rate_limited) if any real call
    has been made recently."""
    settings = get_settings()
    key_by_provider: dict[str, str | None] = {
        "virustotal": settings.virustotal_api_key,
        "abuseipdb": settings.abuseipdb_api_key,
        "shodan": settings.shodan_api_key,
        "otx": settings.otx_api_key,
        "greynoise": settings.greynoise_api_key,
        "abusech": settings.abusech_api_key,
        "urlscan": settings.urlscan_api_key,
        "whois": "no-key-needed",
    }
    health = get_provider_health()

    statuses = []
    for provider in _all_investigate_providers():
        statuses.append(
            IntegrationStatusRead(
                provider=provider.name,
                mode="mocked" if provider.is_mock else "live",
                configured=bool(key_by_provider.get(provider.name)),
                last_status=await health.get_status(provider.name),
                supported_types=sorted(provider.supported_types, key=lambda t: t.value),
            )
        )
    return statuses
