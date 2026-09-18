"""HTTPS-only helpers that do not forward credentials across origins."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import json


DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_JSON_BYTES = 16 * 1024 * 1024
DEFAULT_DOWNLOAD_BYTES = 1024 * 1024 * 1024
COPY_CHUNK_BYTES = 1024 * 1024


def require_https(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"Only credential-free HTTPS URLs are supported: {url!r}")


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), parsed.port


class SafeHTTPSRedirectHandler(HTTPRedirectHandler):
    """Reject non-HTTPS redirects and strip authorization on origin changes."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        require_https(new_url)
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if redirected is not None and _origin(request.full_url) != _origin(new_url):
            redirected.remove_header("Authorization")
        return redirected


def open_https(request: Request, *, timeout: int = DEFAULT_TIMEOUT_SECONDS):
    require_https(request.full_url)
    return build_opener(SafeHTTPSRedirectHandler()).open(request, timeout=timeout)  # nosec B310: HTTPS is enforced above.


def read_limited(response, *, max_bytes: int) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length is not None and int(content_length) > max_bytes:
        raise ValueError("HTTPS response exceeds size limit")
    data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("HTTPS response exceeds size limit")
    return data


def get_json_https(url: str, *, headers: dict[str, str], max_bytes: int = DEFAULT_JSON_BYTES) -> dict:
    request = Request(url, headers=headers)
    with open_https(request) as response:
        payload = read_limited(response, max_bytes=max_bytes)
    return json.loads(payload.decode("utf-8"))


def download_https(
    url: str,
    destination: Path,
    *,
    headers: dict[str, str],
    max_bytes: int = DEFAULT_DOWNLOAD_BYTES,
) -> None:
    request = Request(url, headers=headers)
    total = 0
    try:
        with open_https(request) as response, destination.open("xb") as output:
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > max_bytes:
                raise ValueError("HTTPS download exceeds size limit")
            while chunk := response.read(COPY_CHUNK_BYTES):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("HTTPS download exceeds size limit")
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
