"""Fetch pre-operative documentation HTML over HTTP (VE-22)."""

from __future__ import annotations

import httpx

from preop_rag.config import HTTP_TIMEOUT_SECONDS
from preop_rag.errors import PreopSourceFetchError


def _fetch_with_client(url: str, client: httpx.Client) -> str:
    response = client.get(url, headers={"User-Agent": "vet-es-preop-rag/1.0"})
    if response.status_code != httpx.codes.OK:
        raise PreopSourceFetchError(
            "Pre-op source fetch failed: HTTP "
            f"{response.status_code} for {url!r} (expected 200)"
        )
    text = response.text
    if not text or not text.strip():
        raise PreopSourceFetchError(
            f"Pre-op source fetch failed: empty body for {url!r}"
        )
    return text


def fetch_preop_html(
    url: str,
    *,
    timeout_seconds: float = HTTP_TIMEOUT_SECONDS,
    client: httpx.Client | None = None,
) -> str:
    """GET ``url`` and return response body as text.

    Redirects are followed (httpx default). Non-success status codes raise
    ``PreopSourceFetchError`` with an explicit message (no silent empty body).

    :param url: Document URL.
    :param timeout_seconds: Socket read/connect timeout (default client only).
    :param client: Optional ``httpx.Client`` for tests or custom transports.
    :return: Response body (typically HTML).
    :raises PreopSourceFetchError: On HTTP errors, timeouts, or transport failures.
    """
    if client is not None:
        try:
            return _fetch_with_client(url, client)
        except httpx.RequestError as exc:
            raise PreopSourceFetchError(
                f"Pre-op source fetch failed: network error for {url!r}: {exc}"
            ) from exc

    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
        ) as owned:
            return _fetch_with_client(url, owned)
    except httpx.TimeoutException as exc:
        raise PreopSourceFetchError(
            f"Pre-op source fetch failed: timeout after {timeout_seconds}s for {url!r}"
        ) from exc
    except httpx.RequestError as exc:
        raise PreopSourceFetchError(
            f"Pre-op source fetch failed: network error for {url!r}: {exc}"
        ) from exc
