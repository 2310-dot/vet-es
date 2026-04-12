"""Google Calendar read-only listing tool for the clinic assistant (VE-24).

Lists events in a single configured calendar for a time window using the
Google Calendar API. Credentials and calendar id come from environment
variables only.

OAuth scope (minimum for listing): ``https://www.googleapis.com/auth/calendar.readonly``.

Set ``GOOGLE_CALENDAR_USE_STUB=1`` for deterministic offline tests or local
runs without Google credentials; default is live API when configured.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Final

import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

OAUTH_SCOPE: Final[str] = "https://www.googleapis.com/auth/calendar.readonly"
MAX_EVENTS_PER_RESPONSE: Final[int] = 250
DEFAULT_HTTP_TIMEOUT_SEC: Final[float] = 30.0

_TOOL_DESCRIPTION: Final[str] = (
    "List Google Calendar events in a configured clinic/staff calendar for a "
    "time window. Use RFC 3339 datetimes with explicit timezone offset or Z "
    "(UTC), e.g. 2026-04-11T08:00:00Z. Returns structured events (id, summary, "
    "start, end, status). Staff-side read: do not use raw results to tell "
    "clients internal surgical times; follow docs/event-storming-workflow.md "
    "and docs/reglas-de-negocio-logica-de-agenda.md for client-facing rules."
)


def _truthy_env(name: str) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _http_timeout_seconds() -> float:
    raw = os.environ.get("GOOGLE_CALENDAR_HTTP_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return DEFAULT_HTTP_TIMEOUT_SEC
    try:
        return max(1.0, float(raw))
    except ValueError:
        return DEFAULT_HTTP_TIMEOUT_SEC


def parse_rfc3339_datetime(value: str) -> datetime:
    """Parse a datetime that must include a timezone (``Z`` or numeric offset).

    :param value: RFC 3339-like string.
    :return: Timezone-aware datetime.
    :raises ValueError: If empty, naive, or unparsable.
    """
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("datetime string is empty")
    normalized = cleaned.replace("Z", "+00:00") if cleaned.endswith("Z") else cleaned
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("datetime is not valid ISO / RFC 3339") from exc
    if dt.tzinfo is None:
        raise ValueError(
            "datetime must include timezone (use Z for UTC or a numeric offset)"
        )
    return dt


def _error_payload(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _required_env(name: str) -> str | None:
    val = os.environ.get(name, "").strip()
    return val or None


def _load_credentials() -> Credentials | None:
    """Build OAuth credentials from env; return None if any required var is missing."""
    client_id = _required_env("GOOGLE_CALENDAR_CLIENT_ID")
    client_secret = _required_env("GOOGLE_CALENDAR_CLIENT_SECRET")
    refresh = _required_env("GOOGLE_CALENDAR_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh):
        return None
    return Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[OAUTH_SCOPE],
    )


def is_google_calendar_live_enabled() -> bool:
    """Return True when Calendar API calls should hit Google (not stub, env complete).

    Used by :mod:`tools.availability` to decide whether
    ``check_surgical_availability`` reads occupancy from Calendar.
    """
    if _truthy_env("GOOGLE_CALENDAR_USE_STUB"):
        return False
    if not _required_env("GOOGLE_CALENDAR_ID"):
        return False
    return _load_credentials() is not None


def _event_boundary(ev: dict[str, Any], key: str) -> str:
    block = ev.get(key) or {}
    if not isinstance(block, dict):
        return ""
    if "dateTime" in block:
        return str(block["dateTime"])
    if "date" in block:
        return str(block["date"])
    return ""


def _list_events_stub(
    time_window_start: str,
    time_window_end: str,
) -> dict[str, Any]:
    """Return an empty successful payload (no network)."""
    try:
        start = parse_rfc3339_datetime(time_window_start)
        end = parse_rfc3339_datetime(time_window_end)
    except ValueError as exc:
        return _error_payload("INVALID_DATETIME", str(exc))
    if end <= start:
        return _error_payload(
            "INVALID_WINDOW",
            "time_window_end must be strictly after time_window_start.",
        )
    return {
        "ok": True,
        "provider": "google_calendar",
        "stub": True,
        "oauth_scope": OAUTH_SCOPE,
        "events": [],
        "truncated": False,
        "time_window_start": start.isoformat(),
        "time_window_end": end.isoformat(),
    }


def list_google_calendar_events_impl(
    time_window_start: str,
    time_window_end: str,
) -> dict[str, Any]:
    """List events in the configured calendar (live API or stub).

    :param time_window_start: RFC 3339 with Z or offset.
    :param time_window_end: RFC 3339 with Z or offset.
    :return: JSON-serializable result dict.
    """
    if _truthy_env("GOOGLE_CALENDAR_USE_STUB"):
        return _list_events_stub(time_window_start, time_window_end)

    cal_id = _required_env("GOOGLE_CALENDAR_ID")
    if not cal_id:
        return _error_payload(
            "MISSING_CONFIG",
            "GOOGLE_CALENDAR_ID is not set or empty.",
        )

    creds = _load_credentials()
    if creds is None:
        return _error_payload(
            "MISSING_CONFIG",
            "Google OAuth env vars are incomplete. Required: "
            "GOOGLE_CALENDAR_CLIENT_ID, GOOGLE_CALENDAR_CLIENT_SECRET, "
            "GOOGLE_CALENDAR_REFRESH_TOKEN.",
        )

    try:
        start = parse_rfc3339_datetime(time_window_start)
        end = parse_rfc3339_datetime(time_window_end)
    except ValueError as exc:
        return _error_payload("INVALID_DATETIME", str(exc))

    if end <= start:
        return _error_payload(
            "INVALID_WINDOW",
            "time_window_end must be strictly after time_window_start.",
        )

    try:
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                return _error_payload(
                    "AUTH_ERROR",
                    "Could not obtain valid Google credentials (refresh failed or "
                    "token missing).",
                )
    except Exception:
        logger.exception("Google OAuth refresh failed")
        return _error_payload(
            "AUTH_ERROR",
            "Google authentication failed (invalid, revoked, or expired "
            "credentials).",
        )

    timeout = _http_timeout_seconds()
    http = AuthorizedHttp(
        creds,
        http=httplib2.Http(timeout=timeout),
    )
    try:
        service = build("calendar", "v3", http=http, cache_discovery=False)
        t_min = start.astimezone().isoformat()
        t_max = end.astimezone().isoformat()
        logger.info(
            "Google Calendar API HTTP request to calendar.googleapis.com "
            "(calendar v3 events.list, calendarId=%s)",
            cal_id,
        )
        events_result = (
            service.events()
            .list(
                calendarId=cal_id,
                timeMin=t_min,
                timeMax=t_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=MAX_EVENTS_PER_RESPONSE,
            )
            .execute()
        )
    except HttpError as exc:
        # Never log response bodies (may contain PII).
        logger.error(
            "Google Calendar API error (%s)",
            exc.resp.status if exc.resp else "unknown",
        )
        status = exc.resp.status if exc.resp else None
        if status in {401, 403}:
            return _error_payload(
                "AUTH_ERROR",
                "Google Calendar denied access (check credentials and calendar id).",
            )
        return _error_payload(
            "API_ERROR",
            "Google Calendar API returned an error.",
        )
    except Exception:
        logger.exception("Google Calendar list failed")
        return _error_payload(
            "API_ERROR",
            "An unexpected error occurred while calling Google Calendar.",
        )

    items = events_result.get("items") or []
    truncated = bool(events_result.get("nextPageToken"))
    out_events: list[dict[str, Any]] = []
    for ev in items:
        if not isinstance(ev, dict):
            continue
        out_events.append(
            {
                "id": ev.get("id"),
                "summary": ev.get("summary"),
                "start": _event_boundary(ev, "start"),
                "end": _event_boundary(ev, "end"),
                "status": ev.get("status") or "confirmed",
            }
        )

    return {
        "ok": True,
        "provider": "google_calendar",
        "stub": False,
        "oauth_scope": OAUTH_SCOPE,
        "events": out_events,
        "truncated": truncated,
        "time_window_start": start.isoformat(),
        "time_window_end": end.isoformat(),
    }


list_google_calendar_events = StructuredTool.from_function(
    name="list_google_calendar_events",
    description=_TOOL_DESCRIPTION,
    func=list_google_calendar_events_impl,
)


def google_calendar_tools() -> list[StructuredTool]:
    """Calendar tools bound on the clinic assistant."""
    return [list_google_calendar_events]


def safe_json_for_tool_message(payload: dict[str, Any]) -> str:
    """Serialize tool output for a ToolMessage (stable for the model)."""
    return json.dumps(payload, ensure_ascii=False, default=str)
