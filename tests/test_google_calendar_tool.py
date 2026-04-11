"""Tests for Google Calendar listing tool (VE-24)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from google_calendar_tool import (
    OAUTH_SCOPE,
    list_google_calendar_events,
    list_google_calendar_events_impl,
    parse_rfc3339_datetime,
)


def test_parse_rfc3339_accepts_z_suffix() -> None:
    dt = parse_rfc3339_datetime("2026-04-11T12:00:00Z")
    assert dt.year == 2026
    assert dt.utcoffset() is not None


def test_parse_rfc3339_rejects_naive() -> None:
    with pytest.raises(ValueError, match="timezone"):
        parse_rfc3339_datetime("2026-04-11T12:00:00")


def test_stub_mode_valid_window_empty_events(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CALENDAR_USE_STUB", "1")
    out = list_google_calendar_events_impl(
        "2026-04-11T08:00:00+00:00",
        "2026-04-11T18:00:00+00:00",
    )
    assert out["ok"] is True
    assert out["stub"] is True
    assert out["events"] == []
    assert out["truncated"] is False
    assert out["oauth_scope"] == OAUTH_SCOPE


def test_invalid_window_end_before_start_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CALENDAR_USE_STUB", "1")
    out = list_google_calendar_events_impl(
        "2026-04-11T18:00:00+00:00",
        "2026-04-11T08:00:00+00:00",
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "INVALID_WINDOW"


def test_live_path_missing_calendar_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CALENDAR_USE_STUB", raising=False)
    monkeypatch.delenv("GOOGLE_CALENDAR_ID", raising=False)
    out = list_google_calendar_events_impl(
        "2026-04-11T00:00:00Z",
        "2026-04-11T23:59:59Z",
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "MISSING_CONFIG"


def test_live_path_missing_oauth_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CALENDAR_USE_STUB", raising=False)
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
    for key in (
        "GOOGLE_CALENDAR_CLIENT_ID",
        "GOOGLE_CALENDAR_CLIENT_SECRET",
        "GOOGLE_CALENDAR_REFRESH_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)
    out = list_google_calendar_events_impl(
        "2026-04-11T00:00:00Z",
        "2026-04-11T23:59:59Z",
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "MISSING_CONFIG"


def test_structured_tool_name_and_scope_in_description() -> None:
    tool = list_google_calendar_events
    assert tool.name == "list_google_calendar_events"
    desc = (tool.description or "").lower()
    assert "google" in desc
    assert "rfc" in desc or "3339" in desc


def test_truncated_when_next_page_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CALENDAR_USE_STUB", raising=False)
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "cal@test")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "sec")
    monkeypatch.setenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "ref")

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.expired = False

    fake_exec = MagicMock(
        return_value={
            "items": [
                {
                    "id": "e1",
                    "summary": "A",
                    "start": {"dateTime": "2026-04-11T10:00:00Z"},
                    "end": {"dateTime": "2026-04-11T11:00:00Z"},
                    "status": "confirmed",
                }
            ],
            "nextPageToken": "more",
        }
    )
    fake_list = MagicMock(return_value=MagicMock(execute=fake_exec))
    fake_events = MagicMock(return_value=MagicMock(list=fake_list))
    fake_service = MagicMock(events=fake_events)

    with patch("google_calendar_tool.Credentials", return_value=fake_creds):
        with patch("google_calendar_tool.build", return_value=fake_service):
            out = list_google_calendar_events_impl(
                "2026-04-11T00:00:00Z",
                "2026-04-11T23:59:59Z",
            )
    assert out["ok"] is True
    assert out["truncated"] is True
    assert len(out["events"]) == 1
    assert out["events"][0]["id"] == "e1"


def test_cancelled_event_status_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_CALENDAR_USE_STUB", raising=False)
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "cal@test")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "sec")
    monkeypatch.setenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "ref")

    fake_creds = MagicMock()
    fake_creds.valid = True
    fake_creds.expired = False

    fake_exec = MagicMock(
        return_value={
            "items": [
                {
                    "id": "e2",
                    "summary": "Cancelled meet",
                    "start": {"dateTime": "2026-04-11T14:00:00Z"},
                    "end": {"dateTime": "2026-04-11T15:00:00Z"},
                    "status": "cancelled",
                }
            ],
        }
    )
    fake_list = MagicMock(return_value=MagicMock(execute=fake_exec))
    fake_events = MagicMock(return_value=MagicMock(list=fake_list))
    fake_service = MagicMock(events=fake_events)

    with patch("google_calendar_tool.Credentials", return_value=fake_creds):
        with patch("google_calendar_tool.build", return_value=fake_service):
            out = list_google_calendar_events_impl(
                "2026-04-11T00:00:00Z",
                "2026-04-11T23:59:59Z",
            )
    assert out["ok"] is True
    assert out["events"][0]["status"] == "cancelled"
