from app.core.config import get_settings
from app.integrations.abuseipdb import AbuseIPDBProvider
from app.integrations.base import ThreatIntelProvider
from app.integrations.mock_provider import MockAbuseIPDBProvider, MockVirusTotalProvider
from app.integrations.virustotal import VirusTotalProvider
from app.models.enums import IOCType


def get_enrichment_providers(ioc_type: IOCType) -> list[ThreatIntelProvider]:
    """Real providers when a key is configured and mock mode is off,
    otherwise the built-in mock so enrichment always works with zero keys."""
    settings = get_settings()
    providers: list[ThreatIntelProvider] = []

    if not settings.threat_intel_use_mock:
        if settings.virustotal_api_key:
            providers.append(VirusTotalProvider(settings.virustotal_api_key))
        if settings.abuseipdb_api_key:
            providers.append(AbuseIPDBProvider(settings.abuseipdb_api_key))

    if not providers:
        providers = [MockVirusTotalProvider(), MockAbuseIPDBProvider()]

    return [p for p in providers if ioc_type in p.supported_types]
