import logging

import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.models.enums import IOCType

logger = logging.getLogger(__name__)


class ShodanProvider(ThreatIntelProvider):
    name = "shodan"
    supported_types = frozenset({IOCType.ip})
    base_url = "https://api.shodan.io"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        url = f"{self.base_url}/shodan/host/{value}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params={"key": self.api_key})
                if resp.status_code == 404:
                    return EnrichmentResult(
                        provider=self.name, verdict="unknown", score=None, raw={"found": False}
                    )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Shodan lookup failed for %s: %s", value, exc)
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"error": str(exc)}
            )

        vulns = list(data.get("vulns", []))
        ports = data.get("ports", [])
        verdict = "malicious" if vulns else "suspicious" if ports else "clean"
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=float(min(len(vulns) * 20, 100)) if vulns else 0.0,
            raw={
                "ports": ports,
                "vulns": vulns,
                "org": data.get("org"),
                "tags": data.get("tags", []),
            },
        )
