"""Tests for mock surgical availability tool (VE-29)."""

from __future__ import annotations

import copy

import pytest

from tools.availability import (
    check_availability,
    check_surgical_availability,
    surgical_availability_tools,
)


def test_tool_invoke_weekday_stable_fields() -> None:
    """AC1: tool returns a stable success shape for a weekday."""
    tool = check_surgical_availability
    out = tool.invoke({"date": "2026-04-14"})
    assert isinstance(out, dict)
    assert out["date"] == "2026-04-14"
    assert out["weekday"] == "Tuesday"
    assert out["available"] is True
    assert out["slots_remaining_minutes"] == 120
    assert out["dogs_remaining"] == 2
    assert out["cats_remaining"] == 3
    assert out["intake_windows"]["cats"] == "08:00–09:00"
    assert out["intake_windows"]["dogs"] == "09:00–10:30"
    assert out["source"] == "mock"
    assert "orientativ" in (out.get("note") or "").lower()
    copy.deepcopy(out)


def test_tool_name_and_description_not_real_calendar() -> None:
    """AC3: tool name/description do not claim a real calendar or confirmed booking."""
    tool = check_surgical_availability
    assert tool.name == "check_surgical_availability"
    desc = (tool.description or "").lower()
    assert "orientativ" in desc
    assert "calendario real" not in desc
    assert "reserva confirmada" not in desc


def test_saturday_unavailable() -> None:
    out = check_availability("2026-04-11")
    assert out["available"] is False
    assert out["weekday"] == "Saturday"
    assert "fin de semana" in (out.get("reason") or "").lower()
    assert out["source"] == "mock"


def test_invalid_date_structured_error() -> None:
    out = check_availability("not-a-date")
    assert out["available"] is False
    assert "reason" in out
    assert out["source"] == "mock"
    assert "weekday" not in out


def test_monday_wednesday_sixty_minutes() -> None:
    assert check_availability("2026-04-13")["slots_remaining_minutes"] == 60
    assert check_availability("2026-04-15")["slots_remaining_minutes"] == 60


def test_friday_one_eighty() -> None:
    out = check_availability("2026-04-17")
    assert out["weekday"] == "Friday"
    assert out["slots_remaining_minutes"] == 180
    assert out["dogs_remaining"] == 3


def test_surgical_availability_tools_list() -> None:
    tools = surgical_availability_tools()
    assert any(t.name == "check_surgical_availability" for t in tools)
