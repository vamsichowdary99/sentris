import logging
from datetime import UTC, datetime

import httpx

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.models.enums import IOCType

logger = logging.getLogger(__name__)


class WhoisProvider(ThreatIntelProvider):
    """WHOIS/RDAP — domain age via the public rdap.org bootstrap redirector.
    No API key required; a newly-registered domain is a strong phishing
    signal the AI report weighs alongside the other providers' verdicts."""

    name = "whois"
    supported_types = frozenset({IOCType.domain})
    base_url = "https://rdap.org/domain"

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(f"{self.base_url}/{value}")
                if resp.status_code == 404:
                    return EnrichmentResult(
                        provider=self.name, verdict="unknown", score=None, raw={"found": False}
                    )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            logger.warning("WHOIS/RDAP lookup failed for %s: %s", value, exc)
            return EnrichmentResult(
                provider=self.name, verdict="unknown", score=None, raw={"error": str(exc)}
            )

        registration = next(
            (e for e in data.get("events", []) if e.get("eventAction") == "registration"), None
        )
        age_days = None
        if registration and registration.get("eventDate"):
            registered_at = datetime.fromisoformat(registration["eventDate"].replace("Z", "+00:00"))
            age_days = (datetime.now(UTC) - registered_at).days

        return EnrichmentResult(
            provider=self.name,
            verdict="unknown",
            score=None,
            raw={"found": True, "domain_age_days": age_days},
        )
