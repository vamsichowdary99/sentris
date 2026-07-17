import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.integrations.http_helpers import raise_for_provider_errors
from app.models.enums import IOCType


class AbuseIPDBProvider(ThreatIntelProvider):
    """AbuseIPDB v2 — https://docs.abuseipdb.com/
    Auth: `Key` header. Free tier: 1,000 checks/day."""

    name = "abuseipdb"
    supported_types = frozenset({IOCType.ip})
    base_url = "https://api.abuseipdb.com/api/v2/check"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                self.base_url,
                params={"ipAddress": value, "maxAgeInDays": 90},
                headers={"Key": self.api_key, "Accept": "application/json"},
            )

        if resp.status_code == 404:
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"found": False}
            )
        raise_for_provider_errors(resp)

        attrs = resp.json().get("data", {})
        score = float(attrs.get("abuseConfidenceScore") or 0)
        verdict = "malicious" if score >= 75 else "suspicious" if score >= 25 else "clean"
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=score,
            raw={
                "found": True,
                "abuseConfidenceScore": score,
                "totalReports": attrs.get("totalReports"),
                "countryCode": attrs.get("countryCode"),
                "isp": attrs.get("isp"),
                "isTor": attrs.get("isTor"),
                "usageType": attrs.get("usageType"),
                "lastReportedAt": attrs.get("lastReportedAt"),
            },
        )
