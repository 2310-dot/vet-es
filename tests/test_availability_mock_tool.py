"""Tests for mock Tetris availability tool (VE-23)."""

from __future__ import annotations

import copy

import pytest

from availability_mock_tool import (
    DAILY_CAPACITY_MINUTES,
    compute_mock_day_state,
    get_mock_tetris_availability,
    mock_tetris_booking_tools,
)


def test_ac1_tool_invoke_returns_structured_dict() -> None:
    """AC1: invoke tool and receive structured JSON-serializable data."""
    tool = get_mock_tetris_availability
    out = tool.invoke({"date": "2026-04-13"})
    assert isinstance(out, dict)
    assert out["mock"] is True
    assert out["date"] == "2026-04-13"
    assert out["occupied_minutes"] == 0
    assert out["remaining_minutes"] == DAILY_CAPACITY_MINUTES
    assert out["dogs_scheduled"] == 0
    # Serializable smoke check
    copy.deepcopy(out)


def test_ac2_tool_name_and_description_mention_mock_and_docs() -> None:
    """AC2: stable name and model-facing description states mock + Tetris docs."""
    tool = get_mock_tetris_availability
    assert tool.name == "get_mock_tetris_availability"
    desc = (tool.description or "").lower()
    assert "mock" in desc
    assert "240" in desc
    assert "docs/reglas-de-negocio-logica-de-agenda.md" in (tool.description or "")
    assert "tetris" in desc


def test_ac3_regla1_insufficient_minutes() -> None:
    """AC3: occupied + new duration > 240 → not feasible."""
    out = get_mock_tetris_availability.invoke(
        {
            "date": "2026-04-14",
            "species": "dog",
            "proposed_duration_minutes": 30,
        }
    )
    assert out["occupied_minutes"] == 230
    assert out["remaining_minutes"] == 10
    fc = out["feasibility_check"]
    assert fc["feasible"] is False
    assert fc["reason_code"] == "INSUFFICIENT_MINUTES"


def test_ac3_regla1_exact_fit_feasible() -> None:
    """Boundary: remaining equals requested duration → feasible (≤ 240 rule)."""
    out = get_mock_tetris_availability.invoke(
        {
            "date": "2026-04-14",
            "species": "cat",
            "proposed_duration_minutes": 10,
        }
    )
    fc = out["feasibility_check"]
    assert fc["feasible"] is True
    assert fc["reason_code"] == "OK"


def test_ac4_regla2_two_dogs_blocks_another_dog_cat_still_ok() -> None:
    """AC4: two dogs → no third dog; cat may still fit if minutes allow."""
    day = get_mock_tetris_availability.invoke({"date": "2026-04-15"})
    assert day["dogs_scheduled"] == 2
    assert day["remaining_minutes"] == 140

    dog = get_mock_tetris_availability.invoke(
        {
            "date": "2026-04-15",
            "species": "dog",
            "proposed_duration_minutes": 30,
        }
    )
    assert dog["feasibility_check"]["feasible"] is False
    assert dog["feasibility_check"]["reason_code"] == "DOG_LIMIT_REACHED"

    cat = get_mock_tetris_availability.invoke(
        {
            "date": "2026-04-15",
            "species": "cat",
            "proposed_duration_minutes": 15,
        }
    )
    assert cat["feasibility_check"]["feasible"] is True


def test_ac5_drop_off_windows() -> None:
    """AC5: species drop-off metadata matches reglas §4."""
    out = get_mock_tetris_availability.invoke({"date": "2026-04-13"})
    win = out["constraints"]["drop_off_window"]
    assert win["cat"] == "08:00-09:00"
    assert win["dog"] == "09:00-10:30"


def test_ac6_invalid_date_and_non_operating_day_errors() -> None:
    """AC6: invalid ISO and closed mock days return machine-readable error."""
    bad = compute_mock_day_state("not-a-date")
    assert "error" in bad
    assert bad["error"]["code"] == "INVALID_DATE"

    sunday = compute_mock_day_state("2026-04-12")
    assert sunday["error"]["code"] == "NON_OPERATING_DAY"

    bad_species = get_mock_tetris_availability.invoke(
        {"date": "2026-04-13", "species": "ferret"}
    )
    assert bad_species["error"]["code"] == "INVALID_SPECIES"

    dur_only = get_mock_tetris_availability.invoke(
        {"date": "2026-04-13", "proposed_duration_minutes": 12}
    )
    assert dur_only["error"]["code"] == "INVALID_INPUT"


def test_ac7_empty_day_zero_dogs_full_remaining() -> None:
    """AC7: no bookings → 0 occupied, 240 remaining, 0 dogs."""
    out = compute_mock_day_state("2026-04-13")
    assert out["occupied_minutes"] == 0
    assert out["remaining_minutes"] == DAILY_CAPACITY_MINUTES
    assert out["dogs_scheduled"] == 0


def test_ac7_full_day_remaining_zero() -> None:
    out = compute_mock_day_state("2026-04-16")
    assert out["occupied_minutes"] == 240
    assert out["remaining_minutes"] == 0


def test_ac8_determinism() -> None:
    """AC8: identical inputs → identical payloads."""
    args = {
        "date": "2026-04-15",
        "species": "cat",
        "proposed_duration_minutes": 15,
    }
    a = get_mock_tetris_availability.invoke(args)
    b = get_mock_tetris_availability.invoke(args)
    assert a == b


def test_mock_tetris_booking_tools_includes_registered_tool() -> None:
    tools = mock_tetris_booking_tools()
    assert any(t.name == "get_mock_tetris_availability" for t in tools)


def test_non_positive_duration_rejected() -> None:
    out = get_mock_tetris_availability.invoke(
        {
            "date": "2026-04-13",
            "species": "cat",
            "proposed_duration_minutes": 0,
        }
    )
    assert out["error"]["code"] == "INVALID_INPUT"
