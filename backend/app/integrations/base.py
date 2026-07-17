from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

from app.models.enums import IOCType

VERDICT_RANK = {"unknown": 0, "clean": 1, "suspicious": 2, "malicious": 3}


@dataclass(frozen=True)
class EnrichmentResult:
    provider: str
    verdict: str
    score: float | None
    raw: dict[str, Any]


class ThreatIntelProvider(ABC):
    """A source of IOC reputation data — real (VirusTotal/AbuseIPDB) or mock."""

    name: ClassVar[str]
    supported_types: ClassVar[frozenset[IOCType]]
    # True for Mock* providers — skips client-side rate limiting, which only
    # exists to protect real providers' free-tier quotas.
    is_mock: ClassVar[bool] = False

    @abstractmethod
    async def check(self, ioc_type: IOCType, value: str) -> EnrichmentResult: ...
