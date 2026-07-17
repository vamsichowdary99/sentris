"""Client-side defense for free-tier rate limits, plus a short-lived record
of each real provider's last observed outcome (for GET /integrations/status).

Two mechanisms, both Redis-backed so they're shared across api/worker
processes:
  1. A token bucket per provider — throttles proactively so we rarely
     trigger a real 429 in the first place. VirusTotal's well-documented
     ~4 req/min is the strictest and most important to enforce client-side.
  2. An escalating cooldown set whenever a 429 *does* happen (shared key,
     clock drift, changed limits) — doubles on consecutive hits up to a
     cap, and is checked before the token bucket so a provider mid-cooldown
     is skipped entirely rather than spending a token on a call we already
     know will fail.
"""

import time
from typing import ClassVar

from redis import asyncio as redis_asyncio

from app.core.config import get_settings

# (burst capacity, tokens refilled per minute) — tuned to each free tier's
# documented (or reasonably conservative, where undocumented) limits.
_PROVIDER_LIMITS: dict[str, tuple[int, float]] = {
    "virustotal": (4, 4.0),
    "abuseipdb": (10, 10.0),
    "shodan": (10, 10.0),
    "otx": (10, 10.0),
    "greynoise": (5, 1.0),
    "abusech": (10, 10.0),
    "urlscan": (5, 5.0),
    "whois": (20, 20.0),
}

_DEFAULT_LIMIT = (10, 10.0)

_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_sec = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local bucket = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(bucket[1])
local last_ts = tonumber(bucket[2])
if tokens == nil then
  tokens = capacity
  last_ts = now
end

local elapsed = math.max(0, now - last_ts)
tokens = math.min(capacity, tokens + elapsed * refill_per_sec)

local allowed = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
end

redis.call('HMSET', key, 'tokens', tostring(tokens), 'ts', tostring(now))
redis.call('EXPIRE', key, 3600)
return allowed
"""


class ProviderHealth:
    MAX_BACKOFF_SECONDS: ClassVar[float] = 900.0
    BASE_BACKOFF_SECONDS: ClassVar[float] = 30.0

    def __init__(self) -> None:
        self._redis: redis_asyncio.Redis | None = None

    async def _client(self) -> redis_asyncio.Redis:
        if self._redis is None:
            self._redis = redis_asyncio.from_url(
                get_settings().redis_url, decode_responses=True
            )
        return self._redis

    async def acquire(self, provider: str) -> tuple[bool, float]:
        """Returns (allowed, retry_after_seconds)."""
        client = await self._client()

        cooldown_ttl = await client.ttl(f"ratelimit:cooldown:{provider}")
        if cooldown_ttl and cooldown_ttl > 0:
            return False, float(cooldown_ttl)

        capacity, refill_per_min = _PROVIDER_LIMITS.get(provider, _DEFAULT_LIMIT)
        allowed = await client.eval(  # type: ignore[misc]
            _TOKEN_BUCKET_LUA,
            1,
            f"ratelimit:bucket:{provider}",
            str(capacity),
            str(refill_per_min / 60.0),
            str(time.time()),
        )
        if not int(allowed):
            return False, round(60.0 / max(refill_per_min, 1.0), 1)
        return True, 0.0

    async def record_rate_limited(self, provider: str, retry_after: float | None) -> None:
        client = await self._client()
        strikes = await client.incr(f"ratelimit:strikes:{provider}")
        await client.expire(f"ratelimit:strikes:{provider}", 3600)
        backoff = retry_after or min(
            self.BASE_BACKOFF_SECONDS * (2 ** (strikes - 1)), self.MAX_BACKOFF_SECONDS
        )
        await client.set(f"ratelimit:cooldown:{provider}", "1", ex=int(backoff) + 1)
        await self.record_status(provider, "rate_limited")

    async def record_success(self, provider: str) -> None:
        client = await self._client()
        await client.delete(f"ratelimit:strikes:{provider}")
        await self.record_status(provider, "ok")

    async def record_status(self, provider: str, status: str) -> None:
        client = await self._client()
        await client.set(f"integration:status:{provider}", status, ex=900)

    async def get_status(self, provider: str) -> str | None:
        client = await self._client()
        return await client.get(f"integration:status:{provider}")


_health: ProviderHealth | None = None


def get_provider_health() -> ProviderHealth:
    global _health
    if _health is None:
        _health = ProviderHealth()
    return _health
