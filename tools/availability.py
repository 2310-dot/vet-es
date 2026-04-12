"""Mock surgical-theatre availability tool (VE-29).

Deterministic **mock** data aligned with the VE-29 backlog table: 240-minute daily
quota, weekday patterns for remaining minutes, max 3 dogs / 4 cats per day,
species intake windows. Not a live calendar (``source`` is always ``mock``).
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Final

from langchain_core.tools import StructuredTool

logger = logging.getLogger(__name__)

DAILY_QUOTA_MINUTES: Final[int] = 240
MAX_DOGS_PER_DAY: Final[int] = 3
MAX_CATS_PER_DAY: Final[int] = 4

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

# Mock occupancy pattern (VE-29): Mon/Wed tight, Tue/Thu medium, Fri light.
_MOCK_BY_WEEKDAY: Final[dict[int, tuple[int, int, int]]] = {
    0: (60, 1, 2),  # Monday
    1: (120, 2, 3),  # Tuesday
    2: (60, 1, 1),  # Wednesday
    3: (120, 2, 2),  # Thursday
    4: (180, 3, 3),  # Friday
}

_TOOL_DESCRIPTION: Final[str] = (
    "Consulta la disponibilidad orientativa de quirófano para una fecha dada "
    "(YYYY-MM-DD). Devuelve minutos disponibles y ventanas de ingreso. "
    "Datos orientativos, no confirma reserva."
)


def check_availability(date: str) -> dict[str, Any]:
    """Return mock availability for *date* (``YYYY-MM-DD``).

    Invalid ISO dates return a structured payload (no Python exception).
    Weekends return ``available: false``. Weekdays include capacity fields.

    :param date: Calendar day in ``YYYY-MM-DD`` (leading/trailing spaces stripped).
    :return: JSON-serializable dict with ``source: \"mock\"``.
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

    slots_left, dogs_left, cats_left = _MOCK_BY_WEEKDAY[d.weekday()]
    assert 0 <= slots_left <= DAILY_QUOTA_MINUTES
    assert 0 <= dogs_left <= MAX_DOGS_PER_DAY
    assert 0 <= cats_left <= MAX_CATS_PER_DAY

    return {
        "date": iso,
        "weekday": weekday_name,
        "available": True,
        "slots_remaining_minutes": slots_left,
        "dogs_remaining": dogs_left,
        "cats_remaining": cats_left,
        "intake_windows": dict(INTAKE_WINDOWS),
        "source": "mock",
        "note": ORIENTATIVE_NOTE,
    }


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
