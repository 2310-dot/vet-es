"""Surgical-theatre availability tool (VE-29 mock, VE-30 Google Calendar).

**Mock** (VE-29): deterministic weekday table when ``GOOGLE_CALENDAR_USE_STUB``
is truthy, OAuth env is incomplete, or live Google is disabled.

**Live Google Calendar** (VE-30): when ``is_google_calendar_live_enabled()`` is
true, events are read via :func:`google_calendar_tool.list_google_calendar_events_impl`
(HTTP to ``calendar.googleapis.com``). Event durations map to consumed quota
minutes; all-day events block the full 240-minute quota for that calendar day.
``source`` is ``google_calendar`` instead of ``mock``.

Species slot counts are **not** derived from Calendar; in the Google path
``dogs_remaining`` and ``cats_remaining`` are ``null``. Intake windows are
still returned for agent messaging consistency.
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Final
from zoneinfo import ZoneInfo

from langchain_core.tools import StructuredTool

from google_calendar_tool import (
    is_google_calendar_live_enabled,
    list_google_calendar_events_impl,
    parse_rfc3339_datetime,
)

logger = logging.getLogger(__name__)

DAILY_QUOTA_MINUTES: Final[int] = 240
MAX_DOGS_PER_DAY: Final[int] = 2
MAX_CATS_PER_DAY: Final[int] = 4

CLINIC_TZ: Final[datetime.tzinfo] = ZoneInfo("Europe/Madrid")

INTAKE_WINDOWS: Final[dict[str, str]] = {
    "cats": "08:00–09:00",
    "dogs": "09:00–10:30",
}

ORIENTATIVE_NOTE: Final[str] = (
    "Datos orientativos. La disponibilidad real puede variar."
)

_WEEKDAY_EN: Final[tuple[str, ...]] = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

# Mock occupancy (VE-29): Mon–Thu only per clinic rules; max 2 dogs/day enforced
# in MAX_DOGS_PER_DAY. Thursday simulates two dogs already booked (0 dog slots
# left) while some minute budget remains (Tetris / conv. 9). Tuesday stays open
# for dog slots so a later “try Tuesday” turn can succeed in the mock.
_MOCK_BY_WEEKDAY: Final[dict[int, tuple[int, int, int]]] = {
    0: (60, 1, 2),  # Monday
    1: (120, 2, 2),  # Tuesday
    2: (60, 1, 1),  # Wednesday
    3: (120, 0, 3),  # Thursday — no dog slots left; minutes may still remain
}

_TOOL_DESCRIPTION: Final[str] = (
    "Consulta la disponibilidad orientativa de quirófano para una fecha dada "
    "(YYYY-MM-DD). Cirugía rutinaria: solo lunes a jueves. Devuelve minutos "
    "disponibles, cupo de perros restante (máx. 2/día) y ventanas de ingreso. "
    "Datos orientativos, no confirma reserva."
)


def _day_bounds_local(d: datetime.date) -> tuple[datetime.datetime, datetime.datetime]:
    """Return [start, end) for the calendar day in the clinic timezone."""
    start = datetime.datetime.combine(d, datetime.time.min, tzinfo=CLINIC_TZ)
    end = start + datetime.timedelta(days=1)
    return start, end


def _all_day_covers_date(start_s: str, end_s: str, d: datetime.date) -> bool:
    """Whether an all-day event (Google end date exclusive) covers *d*."""
    sd = datetime.date.fromisoformat(start_s.strip())
    ed = datetime.date.fromisoformat(end_s.strip())
    return sd <= d < ed


def _consumed_minutes_from_google_events(
    events: list[dict[str, Any]],
    d: datetime.date,
) -> int:
    """Sum consumed theatre minutes from normalized Google events for day *d*."""
    day_lo, day_hi = _day_bounds_local(d)
    total = 0
    for ev in events:
        if not isinstance(ev, dict):
            continue
        if (ev.get("status") or "").lower() == "cancelled":
            continue
        start_s = str(ev.get("start") or "").strip()
        end_s = str(ev.get("end") or "").strip()
        if not start_s:
            continue
        if "T" in start_s:
            if not end_s or "T" not in end_s:
                continue
            try:
                st = parse_rfc3339_datetime(start_s)
                et = parse_rfc3339_datetime(end_s)
            except ValueError:
                continue
            seg_a = max(st, day_lo)
            seg_b = min(et, day_hi)
            if seg_b > seg_a:
                total += int((seg_b - seg_a).total_seconds() // 60)
        else:
            if not end_s:
                end_s = start_s
            if _all_day_covers_date(start_s, end_s, d):
                total += DAILY_QUOTA_MINUTES
    return min(DAILY_QUOTA_MINUTES, total)


def _check_availability_mock(d: datetime.date) -> dict[str, Any]:
    """VE-29 deterministic mock for an operating day *d* (Monday–Thursday)."""
    iso = d.isoformat()
    weekday_name = _WEEKDAY_EN[d.weekday()]
    slots_left, dogs_left, cats_left = _MOCK_BY_WEEKDAY[d.weekday()]
    assert 0 <= slots_left <= DAILY_QUOTA_MINUTES
    assert 0 <= dogs_left <= MAX_DOGS_PER_DAY
    assert 0 <= cats_left <= MAX_CATS_PER_DAY
    available = slots_left > 0
    out: dict[str, Any] = {
        "date": iso,
        "weekday": weekday_name,
        "available": available,
        "slots_remaining_minutes": slots_left,
        "dogs_remaining": dogs_left,
        "cats_remaining": cats_left,
        "intake_windows": dict(INTAKE_WINDOWS),
        "source": "mock",
        "note": ORIENTATIVE_NOTE,
    }
    if not available:
        out["reason"] = (
            "Cuota diaria orientativa de quirófano completa para esta fecha (mock)."
        )
    return out


def _check_availability_google(d: datetime.date) -> dict[str, Any]:
    """Build availability from Google Calendar events for local calendar day *d*."""
    iso = d.isoformat()
    weekday_name = _WEEKDAY_EN[d.weekday()]
    day_lo, day_hi = _day_bounds_local(d)
    t_start = day_lo.isoformat()
    t_end = day_hi.isoformat()

    payload = list_google_calendar_events_impl(t_start, t_end)
    if not payload.get("ok"):
        err = payload.get("error") or {}
        msg = str(err.get("message") or "Error al consultar Google Calendar.")
        return {
            "date": iso,
            "weekday": weekday_name,
            "available": False,
            "reason": msg,
            "source": "google_calendar",
        }

    events = payload.get("events") or []
    truncated = bool(payload.get("truncated"))
    consumed = _consumed_minutes_from_google_events(
        events if isinstance(events, list) else [],
        d,
    )
    remaining = max(0, DAILY_QUOTA_MINUTES - consumed)
    note_parts = [ORIENTATIVE_NOTE]
    if truncated:
        note_parts.append(
            "Lista de eventos truncada; la ocupación real podría ser mayor."
        )
    note_parts.append(
        "Perfiles perro/gato no se infieren del calendario (solo cuota por minutos)."
    )
    out: dict[str, Any] = {
        "date": iso,
        "weekday": weekday_name,
        "available": remaining > 0,
        "slots_remaining_minutes": remaining,
        "dogs_remaining": None,
        "cats_remaining": None,
        "intake_windows": dict(INTAKE_WINDOWS),
        "source": "google_calendar",
        "note": " ".join(note_parts),
    }
    if remaining <= 0:
        out["reason"] = (
            "Cuota diaria orientativa de quirófano completa para esta fecha "
            "(según eventos del calendario)."
        )
    return out


def check_availability(date: str) -> dict[str, Any]:
    """Return orientative availability for *date* (``YYYY-MM-DD``).

    Uses Google Calendar when :func:`is_google_calendar_live_enabled` is true;
    otherwise the VE-29 mock table. Invalid ISO dates return a structured
    payload (no Python exception). Friday and weekends return
    ``available: false`` (surgery Mon–Thu only).

    :param date: Calendar day in ``YYYY-MM-DD`` (leading/trailing spaces stripped).
    :return: JSON-serializable dict with ``source`` ``mock`` or ``google_calendar``.
    """
    raw = date.strip()
    try:
        d = datetime.date.fromisoformat(raw)
    except ValueError:
        return {
            "date": raw,
            "available": False,
            "reason": "Formato de fecha no válido; use YYYY-MM-DD.",
            "source": "mock",
        }

    iso = d.isoformat()
    weekday_name = _WEEKDAY_EN[d.weekday()]

    if d.weekday() >= 5:
        return {
            "date": iso,
            "weekday": weekday_name,
            "available": False,
            "reason": "No hay actividad quirúrgica en fin de semana.",
            "source": "mock",
        }

    if d.weekday() == 4:
        return {
            "date": iso,
            "weekday": weekday_name,
            "available": False,
            "reason": (
                "No hay cirugía programada los viernes; días quirúrgicos: lunes a jueves."
            ),
            "source": "mock",
        }

    if is_google_calendar_live_enabled():
        return _check_availability_google(d)

    return _check_availability_mock(d)


def _check_surgical_availability_impl(date: str) -> dict[str, Any]:
    """LangChain entrypoint; logs invocation for operator visibility."""
    logger.info(
        '[tool] check_surgical_availability called with date="%s"',
        date,
    )
    result = check_availability(date)
    compact = {
        k: result[k]
        for k in ("date", "available", "slots_remaining_minutes", "source")
        if k in result
    }
    logger.info("[tool] Response: %s", json.dumps(compact, ensure_ascii=False))
    return result


check_surgical_availability = StructuredTool.from_function(
    name="check_surgical_availability",
    description=_TOOL_DESCRIPTION,
    func=_check_surgical_availability_impl,
)


def surgical_availability_tools() -> list[StructuredTool]:
    """Tools bound on the clinic chat model (VE-29)."""
    return [check_surgical_availability]
