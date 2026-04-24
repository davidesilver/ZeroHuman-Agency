"""URL safety helpers — guard against SSRF when forwarding user-influenced URLs.

Used when passing media URLs (brand assets, generated images) to external
services like Postiz so an attacker-controlled URL can't target private
networks or non-HTTP schemes.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"https"}


class UnsafeURLError(ValueError):
    """Raised when a URL fails safety validation."""


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # Unparseable = treat as unsafe
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_safe_public_url(url: str, *, allow_http: bool = False) -> None:
    """Raise UnsafeURLError if the URL is not a safe public https:// target.

    Rules:
      - Scheme must be https (http allowed only when allow_http=True, e.g. local dev).
      - Host must resolve to a public, routable IP.
      - No userinfo, no non-standard ports blocked explicitly here — rely
        on scheme + IP resolution as the primary gate.
    """
    if not url or not isinstance(url, str):
        raise UnsafeURLError("URL must be a non-empty string")

    parsed = urlparse(url)
    schemes = ALLOWED_SCHEMES | ({"http"} if allow_http else set())
    if parsed.scheme not in schemes:
        raise UnsafeURLError(f"Scheme {parsed.scheme!r} not allowed (require https)")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL has no hostname")

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise UnsafeURLError(f"Host {host!r} does not resolve: {e}") from e

    for info in infos:
        ip = info[4][0]
        if _is_private_ip(ip):
            raise UnsafeURLError(
                f"Host {host!r} resolves to non-public address {ip}"
            )
