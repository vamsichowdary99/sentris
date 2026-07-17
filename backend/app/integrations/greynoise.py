import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.integrations.http_helpers import raise_for_provider_errors
from app.models.enums import IOCType


class GreyNoiseProvider(ThreatIntelProvider):
    """GreyNoise Community v3 — https://docs.greynoise.io/reference/get_v3-community-ip
    Auth: `key` header (lowercase). Free tier: ~50 lookups/week. 404 means
    "not observed scanning the internet or in RIOT" — a valid result, the
    key signal for reconciling conflicts with verdict-only sources."""

    name = "greynoise"
    supported_types = frozenset({IOCType.ip})
    base_url = "https://api.greynoise.io/v3/community"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/{value}", headers={"key": self.api_key})

        if resp.status_code == 404:
            return EnrichmentResult(
                provider=self.name,
                verdict="unknown",
                score=None,
                raw={"classification": "unknown", "noise": False, "seen": False},
            )
        raise_for_provider_errors(resp)

        data = resp.json()
        classification = data.get("classification") or "unknown"
        verdict = {"malicious": "malicious", "benign": "clean"}.get(classification, "unknown")
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score={"malicious": 90.0, "benign": 5.0}.get(classification),
            raw={
                "classification": classification,
                "noise": bool(data.get("noise")),
                "riot": bool(data.get("riot")),
                "name": data.get("name"),
                "last_seen": data.get("last_seen"),
            },
        )
