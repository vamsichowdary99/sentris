import logging

import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.models.enums import IOCType

logger = logging.getLogger(__name__)


class AbuseChProvider(ThreatIntelProvider):
    """abuse.ch ThreatFox — malware-family attribution for hashes/domains/URLs."""

    name = "abusech"
    supported_types = frozenset({IOCType.hash, IOCType.domain, IOCType.url})
    base_url = "https://threatfox-api.abuse.ch/api/v1/"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.base_url,
                    json={"query": "search_ioc", "search_term": value},
                    headers={"Auth-Key": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("abuse.ch lookup failed for %s: %s", value, exc)
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"error": str(exc)}
            )

        if data.get("query_status") != "ok" or not data.get("data"):
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"found": False}
            )

        match = data["data"][0]
        return EnrichmentResult(
            provider=self.name,
            verdict="malicious",
            score=95.0,
            raw={
                "found": True,
                "malware_family": match.get("malware_printable") or match.get("malware"),
                "confidence_level": match.get("confidence_level"),
            },
        )
