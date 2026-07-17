import base64

import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.integrations.http_helpers import raise_for_provider_errors
from app.models.enums import IOCType

_ENDPOINTS = {
    IOCType.ip: "ip_addresses",
    IOCType.domain: "domains",
    IOCType.hash: "files",
    IOCType.url: "urls",
}


class VirusTotalProvider(ThreatIntelProvider):
    """VirusTotal v3 — https://docs.virustotal.com/reference/overview
    Auth: `x-apikey` header. Free public tier: ~4 req/min, ~500/day."""

    name = "virustotal"
    supported_types = frozenset({IOCType.ip, IOCType.domain, IOCType.hash, IOCType.url})
    base_url = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _resource_id(self, ioc_type: IOCType, value: str) -> str:
        if ioc_type == IOCType.url:
            return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
        return value

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        url = f"{self.base_url}/{_ENDPOINTS[ioc_type]}/{self._resource_id(ioc_type, value)}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"x-apikey": self.api_key})

        if resp.status_code == 404:
            # A valid result: VT has never scanned this indicator.
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"found": False}
            )
        raise_for_provider_errors(resp)

        attrs = resp.json().get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats") or {}
        malicious = stats.get("malicious") or 0
        suspicious = stats.get("suspicious") or 0
        total = sum(v for v in stats.values() if isinstance(v, int)) or 1

        verdict = "malicious" if malicious > 0 else "suspicious" if suspicious > 0 else "clean"
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=round(100 * malicious / total, 1),
            raw={
                "found": True,
                "last_analysis_stats": stats,
                "reputation": attrs.get("reputation"),
                "country": attrs.get("country"),
                "asn": attrs.get("asn"),
                "as_owner": attrs.get("as_owner"),
            },
        )
