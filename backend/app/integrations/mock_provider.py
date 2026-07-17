import hashlib
from typing import Any

from app.integrations.base import EnrichmentResult, ThreatIntelProvider
from app.models.enums import IOCType

# Curated so the bundled alert simulator datasets tell a consistent story —
# these values reappear across scenarios and always resolve the same way.
KNOWN_MALICIOUS: frozenset[str] = frozenset(
    {
        "185.220.101.45",
        "45.155.205.233",
        "194.165.16.71",
        "103.224.182.245",
        "cdn-update-service.duckdns.org",
        "secure-office365-login.com",
        "a91f2c6e8b3d4f1a9c7e5b2d8f4a6c1e3b9d7f5a2c8e4b6d1f9a3c7e5b8d2f4a",
    }
)

KNOWN_SUSPICIOUS: frozenset[str] = frozenset(
    {
        "91.219.237.14",
        "146.70.87.192",
        "update-check-cdn.net",
    }
)

# Deliberately conflicting with VT/AbuseIPDB (which classify it "malicious"
# via _classify) — GreyNoise only sees internet-wide scan traffic, and this
# IP is the simulator's port-scan source: a real mass-scanner would show up
# there as benign background noise, not a targeted attacker. This is the
# Investigate module's demo case for AI conflict reconciliation.
GREYNOISE_BENIGN_SCANNER = "194.165.16.71"

# Curated so one investigated indicator gets rich, named attribution instead
# of a generic "malicious" — the "wow" case for the AI report's attribution
# section.
ATTRIBUTED_INDICATORS: dict[str, dict[str, str]] = {
    "a91f2c6e8b3d4f1a9c7e5b2d8f4a6c1e3b9d7f5a2c8e4b6d1f9a3c7e5b8d2f4a": {
        "malware_family": "Emotet",
        "campaign": "SilentTrinity",
        "threat_actor": "APT-Ghost",
    },
    "cdn-update-service.duckdns.org": {
        "malware_family": "Emotet",
        "campaign": "SilentTrinity",
        "threat_actor": "APT-Ghost",
    },
}


def _classify(value: str) -> str:
    """Deterministic verdict: curated values first, otherwise a stable
    hash-derived bucket so the same IOC always resolves the same way while
    unclassified demo traffic still gets some variety (~70/18/12 split)."""
    if value in KNOWN_MALICIOUS:
        return "malicious"
    if value in KNOWN_SUSPICIOUS:
        return "suspicious"
    bucket = int(hashlib.sha256(value.encode()).hexdigest(), 16) % 100
    if bucket < 70:
        return "clean"
    if bucket < 88:
        return "suspicious"
    return "malicious"


class MockVirusTotalProvider(ThreatIntelProvider):
    name = "virustotal"
    is_mock = True
    supported_types = frozenset({IOCType.ip, IOCType.domain, IOCType.hash, IOCType.url})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        verdict = _classify(value)
        stats = {
            "malicious": {"malicious": 14, "suspicious": 3, "harmless": 68, "undetected": 5},
            "suspicious": {"malicious": 1, "suspicious": 6, "harmless": 71, "undetected": 8},
            "clean": {"malicious": 0, "suspicious": 0, "harmless": 78, "undetected": 8},
        }[verdict]
        total = sum(stats.values())
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=round(100 * stats["malicious"] / total, 1),
            raw={
                "mock": True,
                "ioc_type": str(ioc_type),
                "last_analysis_stats": stats,
            },
        )


class MockAbuseIPDBProvider(ThreatIntelProvider):
    name = "abuseipdb"
    is_mock = True
    supported_types = frozenset({IOCType.ip})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        verdict = _classify(value)
        score = {"malicious": 92.0, "suspicious": 38.0, "clean": 0.0}[verdict]
        total_reports = {"malicious": 47, "suspicious": 6, "clean": 0}[verdict]
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=score,
            raw={
                "mock": True,
                "abuseConfidenceScore": score,
                "totalReports": total_reports,
                "countryCode": "RO" if verdict == "malicious" else "US",
                "isp": "Bulletproof Hosting LLC" if verdict == "malicious" else "Example ISP",
            },
        )


class MockShodanProvider(ThreatIntelProvider):
    name = "shodan"
    is_mock = True
    supported_types = frozenset({IOCType.ip})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        verdict = _classify(value)
        profiles: dict[str, dict[str, Any]] = {
            "malicious": {
                "ports": [22, 23, 445, 3389, 8080],
                "vulns": ["CVE-2021-44228", "CVE-2020-1472"],
                "tags": ["compromised", "botnet"],
                "org": "Bulletproof Hosting LLC",
            },
            "suspicious": {
                "ports": [22, 80, 443],
                "vulns": [],
                "tags": ["scanner"],
                "org": "Generic Hosting Ltd",
            },
            "clean": {"ports": [443, 80], "vulns": [], "tags": [], "org": "Example Cloud Inc"},
        }
        profile = profiles[verdict]
        score = {"malicious": 80.0, "suspicious": 40.0, "clean": 0.0}[verdict]
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=score,
            raw={"mock": True, **profile},
        )


class MockOTXProvider(ThreatIntelProvider):
    name = "otx"
    is_mock = True
    supported_types = frozenset({IOCType.ip, IOCType.domain, IOCType.hash, IOCType.url})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        verdict = _classify(value)
        attribution = ATTRIBUTED_INDICATORS.get(value)
        pulse_count = {"malicious": 12, "suspicious": 2, "clean": 0}[verdict]
        malware_families = (
            [attribution["malware_family"]]
            if attribution
            else (["Generic Trojan"] if verdict == "malicious" else [])
        )
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=float(min(pulse_count * 8, 100)),
            raw={
                "mock": True,
                "pulse_count": pulse_count,
                "malware_families": malware_families,
                "adversary": attribution["threat_actor"] if attribution else None,
                "campaign": attribution["campaign"] if attribution else None,
            },
        )


class MockGreyNoiseProvider(ThreatIntelProvider):
    name = "greynoise"
    is_mock = True
    supported_types = frozenset({IOCType.ip})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        if value == GREYNOISE_BENIGN_SCANNER:
            return EnrichmentResult(
                provider=self.name,
                verdict="clean",
                score=5.0,
                raw={
                    "mock": True,
                    "classification": "benign",
                    "noise": True,
                    "riot": False,
                    "tags": ["mass scanner"],
                    "note": "Internet-wide scan traffic, not a targeted attacker.",
                },
            )

        verdict = _classify(value)
        if verdict == "malicious":
            return EnrichmentResult(
                provider=self.name,
                verdict="malicious",
                score=90.0,
                raw={
                    "mock": True,
                    "classification": "malicious",
                    "noise": False,
                    "riot": False,
                    "tags": ["brute forcer"],
                },
            )
        # GreyNoise only has visibility into internet-scanning traffic — most
        # benign/unremarkable IPs simply have no record, which is itself a
        # valid, displayed result rather than an error.
        return EnrichmentResult(
            provider=self.name,
            verdict="unknown",
            score=None,
            raw={"mock": True, "classification": "unknown", "noise": False, "seen": False},
        )


class MockAbuseChProvider(ThreatIntelProvider):
    name = "abusech"
    is_mock = True
    supported_types = frozenset({IOCType.hash, IOCType.domain, IOCType.url})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        verdict = _classify(value)
        if verdict != "malicious":
            return EnrichmentResult(
                provider=self.name,
                verdict="unknown",
                score=None,
                raw={"mock": True, "found": False},
            )
        attribution = ATTRIBUTED_INDICATORS.get(value)
        malware_family = attribution["malware_family"] if attribution else "Generic.Malware"
        return EnrichmentResult(
            provider=self.name,
            verdict="malicious",
            score=95.0,
            raw={
                "mock": True,
                "found": True,
                "malware_family": malware_family,
                "confidence_level": "high" if attribution else "medium",
            },
        )


class MockUrlscanProvider(ThreatIntelProvider):
    name = "urlscan"
    is_mock = True
    supported_types = frozenset({IOCType.domain, IOCType.url})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        verdict = _classify(value)
        digest = hashlib.sha256(value.encode()).hexdigest()[:16]
        profile = {
            "malicious": {"resource_count": 47, "redirect_count": 3},
            "suspicious": {"resource_count": 15, "redirect_count": 1},
            "clean": {"resource_count": 6, "redirect_count": 0},
        }[verdict]
        score = {"malicious": 85.0, "suspicious": 35.0, "clean": 0.0}[verdict]
        return EnrichmentResult(
            provider=self.name,
            verdict=verdict,
            score=score,
            raw={
                "mock": True,
                "screenshot_url": f"https://urlscan.io/screenshots/mock/{digest}.png",
                **profile,
            },
        )


class MockWhoisProvider(ThreatIntelProvider):
    """Domain age only — WHOIS/RDAP isn't a verdict source, so this always
    returns verdict="unknown" and lets the AI interpret a young registration
    date as a phishing signal in context of the other providers' verdicts."""

    name = "whois"
    is_mock = True
    supported_types = frozenset({IOCType.domain})

    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult:
        curated_age = {
            "secure-office365-login.com": 4,
            "cdn-update-service.duckdns.org": 12,
        }
        if value in curated_age:
            age_days = curated_age[value]
        else:
            bucket = int(hashlib.sha256(value.encode()).hexdigest(), 16) % 3000
            age_days = bucket + 30

        return EnrichmentResult(
            provider=self.name,
            verdict="unknown",
            score=None,
            raw={"mock": True, "domain_age_days": age_days, "registrar": "Example Registrar Inc"},
        )
