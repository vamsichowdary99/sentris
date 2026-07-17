"""Detects the IOC type of a pasted indicator (IP/domain/URL/hash) so the
Investigate module can route it to the right threat-intel providers without
the analyst having to specify a type. Order matters: URL (explicit scheme)
and IP (unambiguous via ipaddress) are checked before the hex-hash and
domain fallbacks, since a hash could otherwise look like a very short
all-hex "domain" and an IP would never validate as one anyway.
"""

import ipaddress
import re

from app.models.enums import IOCType

_MAX_LENGTH = 2048
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_HASH_RE = re.compile(r"^[a-fA-F0-9]+$")
_HASH_LENGTHS = {32, 40, 64}  # md5, sha1, sha256
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
)


def detect_indicator_type(raw: str) -> tuple[IOCType, str] | None:
    """Returns (type, normalized_value) or None if the input isn't a
    recognizable indicator at all — callers should surface a clean
    "invalid indicator" error rather than guessing."""
    value = raw.strip()
    if not value or len(value) > _MAX_LENGTH or " " in value:
        return None

    if _URL_RE.match(value):
        return IOCType.url, value

    try:
        ipaddress.ip_address(value)
        return IOCType.ip, value
    except ValueError:
        pass

    if _HASH_RE.match(value) and len(value) in _HASH_LENGTHS:
        return IOCType.hash, value.lower()

    if _DOMAIN_RE.match(value):
        return IOCType.domain, value.lower()

    return None
