"""Mock surgery-day availability tool for the clinic agent (VE-23).

Returns deterministic **mock** agenda state aligned with Tetris rules in
``docs/reglas-de-negocio-logica-de-agenda.md`` (240-minute quota, max two dogs
per day, drop-off windows). Not connected to a live calendar.

**Mock interpretation:** surgery bookable days are **Monday–Thursday** only
(operating days per doc §1). Friday–Sunday yield a structured error.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Final, Literal

from langchain_core.tools import StructuredTool

DAILY_CAPACITY_MINUTES: Final[int] = 240
MAX_DOGS_PER_DAY: Final[int] = 2

# Species-specific drop-off windows (reglas §4); client does not pick surgical times.
DROP_OFF_WINDOW_CAT: Final[str] = "08:00-09:00"
DROP_OFF_WINDOW_DOG: Final[str] = "09:00-10:30"

MOCK_DOCS_REFERENCE: Final[str] = "docs/reglas-de-negocio-logica-de-agenda.md"

# Model-facing description (AC2): explicit MOCK + Tetris / docs alignment.
_TOOL_MODEL_DESCRIPTION: Final[str] = (
    "MOCK (non-production) surgery-day Tetris availability read-model. "
    "Returns deterministic fictional occupancy for ISO date YYYY-MM-DD using "
    "clinic rules in docs/reglas-de-negocio-logica-de-agenda.md: 240-minute "
    "daily quota (Regla 1), max 2 dogs per day (Regla 2), species drop-off "
    "windows cat 08:00-09:00 and dog 09:00-10:30 (§4). Mock bookable days are "
    "Monday–Thursday (§1); Friday–Sunday return a structured error. Optional "
    "species dog|cat plus proposed_duration_minutes adds feasibility_check."
)


@dataclass(frozen=True)
class _FixtureDay:
    """Single mock day: occupied OR minutes and dog count must stay valid."""

    occupied_minutes: int
    dogs_scheduled: int


# Fixed ISO dates (weekdays verified for April 2026): Mon–Thu fixtures.
_MOCK_FIXTURES: dict[str, _FixtureDay] = {
    "2026-04-14": _FixtureDay(230, 0),  # Tuesday: Regla 1 stress (10 min left)
    "2026-04-15": _FixtureDay(100, 2),  # Wednesday: Regla 2 blocks another dog
    "2026-04-16": _FixtureDay(240, 1),  # Thursday: full quota, boundary
}


def _is_operating_weekday(d: date) -> bool:
    """Monday=0 … Sunday=6; surgery operating days Mon–Thu per reglas §1."""
    return d.weekday() <= 3


def _parse_iso_date(date_iso: str) -> date:
    return date.fromisoformat(date_iso.strip())


def _normalize_species(raw: str | None) -> Literal["dog", "cat"] | None:
    if raw is None or raw == "":
        return None
    s = raw.strip().lower()
    if s == "dog":
        return "dog"
    if s == "cat":
        return "cat"
    return None


def _error_payload(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def _feasibility(
    *,
    species: Literal["dog", "cat"],
    proposed_duration_minutes: int,
    remaining_minutes: int,
    dogs_scheduled: int,
) -> dict[str, Any]:
    if species == "dog":
        if dogs_scheduled >= MAX_DOGS_PER_DAY:
            return {
                "species": species,
                "proposed_duration_minutes": proposed_duration_minutes,
                "feasible": False,
                "reason_code": "DOG_LIMIT_REACHED",
            }
        if remaining_minutes < proposed_duration_minutes:
            return {
                "species": species,
                "proposed_duration_minutes": proposed_duration_minutes,
                "feasible": False,
                "reason_code": "INSUFFICIENT_MINUTES",
            }
        return {
            "species": species,
            "proposed_duration_minutes": proposed_duration_minutes,
            "feasible": True,
            "reason_code": "OK",
        }
    # cat: Regla 2 does not apply
    if remaining_minutes < proposed_duration_minutes:
        return {
            "species": species,
            "proposed_duration_minutes": proposed_duration_minutes,
            "feasible": False,
            "reason_code": "INSUFFICIENT_MINUTES",
        }
    return {
        "species": species,
        "proposed_duration_minutes": proposed_duration_minutes,
        "feasible": True,
        "reason_code": "OK",
    }


def compute_mock_day_state(date_iso: str) -> dict[str, Any]:
    """Pure helper: same inputs as the LangChain tool, returns the payload dict.

    Used by tests and callers that do not need ``StructuredTool`` wrapping.

    :param date_iso: ``YYYY-MM-DD``.
    :return: JSON-serializable dict (may include ``error``).
    """
    try:
        d = _parse_iso_date(date_iso)
    except ValueError:
        return {
            "mock": True,
            "date": date_iso.strip(),
            "error": _error_payload(
                "INVALID_DATE",
                "date must be a valid ISO calendar day (YYYY-MM-DD).",
            ),
        }

    iso = d.isoformat()
    if not _is_operating_weekday(d):
        return {
            "mock": True,
            "date": iso,
            "operating_day": False,
            "error": _error_payload(
                "NON_OPERATING_DAY",
                "Mock surgery days are Monday–Thursday only (reglas §1).",
            ),
        }

    fixture = _MOCK_FIXTURES.get(iso)
    if fixture is None:
        occupied = 0
        dogs = 0
    else:
        occupied = fixture.occupied_minutes
        dogs = fixture.dogs_scheduled

    remaining = DAILY_CAPACITY_MINUTES - occupied
    base: dict[str, Any] = {
        "mock": True,
        "date": iso,
        "operating_day": True,
        "docs_reference": MOCK_DOCS_REFERENCE,
        "occupied_minutes": occupied,
        "remaining_minutes": remaining,
        "dogs_scheduled": dogs,
        "constraints": {
            "daily_capacity_minutes": DAILY_CAPACITY_MINUTES,
            "max_dogs_per_day": MAX_DOGS_PER_DAY,
            "drop_off_window": {
                "cat": DROP_OFF_WINDOW_CAT,
                "dog": DROP_OFF_WINDOW_DOG,
            },
        },
    }
    return base


def _get_mock_tetris_availability_impl(
    date: str,
    species: str | None = None,
    proposed_duration_minutes: int | None = None,
) -> dict[str, Any]:
    """Implementation for :data:`get_mock_tetris_availability` (see tool description)."""
    base = compute_mock_day_state(date)
    if "error" in base:
        return base

    norm = _normalize_species(species)
    if species not in (None, "") and norm is None:
        return {
            **base,
            "error": _error_payload(
                "INVALID_SPECIES",
                'species must be omitted, "dog", or "cat" (case-insensitive).',
            ),
        }

    if proposed_duration_minutes is not None and norm is None:
        return {
            **base,
            "error": _error_payload(
                "INVALID_INPUT",
                "proposed_duration_minutes requires species (dog or cat).",
            ),
        }

    if proposed_duration_minutes is not None:
        if proposed_duration_minutes <= 0:
            return {
                **base,
                "error": _error_payload(
                    "INVALID_INPUT",
                    "proposed_duration_minutes must be a positive integer.",
                ),
            }
        assert norm is not None
        remaining = int(base["remaining_minutes"])
        dogs = int(base["dogs_scheduled"])
        base["feasibility_check"] = _feasibility(
            species=norm,
            proposed_duration_minutes=proposed_duration_minutes,
            remaining_minutes=remaining,
            dogs_scheduled=dogs,
        )

    return base


get_mock_tetris_availability = StructuredTool.from_function(
    name="get_mock_tetris_availability",
    description=_TOOL_MODEL_DESCRIPTION,
    func=_get_mock_tetris_availability_impl,
)


def mock_tetris_booking_tools() -> list[StructuredTool]:
    """Tools to bind on the booking / orchestration agent."""
    return [get_mock_tetris_availability]
