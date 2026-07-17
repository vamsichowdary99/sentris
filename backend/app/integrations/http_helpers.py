import httpx


class ProviderAuthError(Exception):
    """401/403 — the configured API key is missing, invalid, or revoked."""


class ProviderRateLimitError(Exception):
    """429 — the provider's own rate limit was hit despite client-side
    throttling (e.g. the key is shared elsewhere, or limits changed)."""

    def __init__(self, retry_after: float | None) -> None:
        self.retry_after = retry_after
        super().__init__(f"rate limited, retry_after={retry_after}")


def raise_for_provider_errors(resp: httpx.Response) -> None:
    """Classifies auth/rate-limit failures distinctly so the service layer
    can report "misconfigured"/"rate_limited" instead of a generic error.
    A plain 404 is deliberately NOT handled here — callers must check
    resp.status_code == 404 themselves and return a clean "not found"
    result, since that's a valid result for a threat-intel lookup, not a
    failure.
    """
    if resp.status_code in (401, 403):
        raise ProviderAuthError(f"authentication failed ({resp.status_code})")
    if resp.status_code == 429:
        retry_after_header = resp.headers.get("Retry-After")
        retry_after = float(retry_after_header) if retry_after_header else None
        raise ProviderRateLimitError(retry_after)
    resp.raise_for_status()
