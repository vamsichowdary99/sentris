import sys

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

# Disabled under pytest: httpx's ASGI transport has no real client IP, so
# every request in a test run buckets under the same key — a handful of
# auth tests would trip the login rate limit and fail on 429s that have
# nothing to do with what they're testing. Checking `"pytest" in
# sys.modules` (true for the whole process once pytest starts, unlike
# PYTEST_CURRENT_TEST which is only set during a test's call phase —
# too late, since this module is imported during collection).
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    enabled="pytest" not in sys.modules,
)
