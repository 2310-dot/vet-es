"""Tests for main.py: Chatbot v4 placeholder API (VETES-16, VE-18, VE-19, VE-21)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from conversation_memory import reset_chat_memory_for_tests, session_messages_copy
from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_chat_memory() -> None:
    """Isolate tests: in-process memory persists on the app module."""
    reset_chat_memory_for_tests()
    yield
    reset_chat_memory_for_tests()


def test_get_health_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_post_chat_json_ok(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        json={"msg": "  hello  ", "session_id": "s1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["msg"] == "hello"
    assert data["session_id"] == "s1"
    assert data["placeholder"] is True
    assert data["turn_count"] == 1


def test_post_chat_empty_msg_422(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        json={"msg": "   ", "session_id": "s1"},
    )
    assert resp.status_code == 422


def test_post_chat_urlencoded_expects_422(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        content=b"msg=hello&session_id=s1",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 422


def test_get_home_returns_html(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"].lower()
    html_body = resp.text
    assert html_body.strip()
    assert "chatbot" in html_body.lower()
    assert 'data-testid="chat-log"' in html_body
    assert "/static/chat_config.js" in html_body


def test_get_static_chat_config(client: TestClient) -> None:
    resp = client.get("/static/chat_config.js")
    assert resp.status_code == 200
    assert "CHATBOT_API_BASE" in resp.text


def test_get_static_chat_js(client: TestClient) -> None:
    resp = client.get("/static/chat.js")
    assert resp.status_code == 200
    assert "fetch" in resp.text


def test_post_ask_bot_urlencoded_ok(client: TestClient) -> None:
    resp = client.post(
        "/ask_bot",
        content=b"msg=hello&session_id=s1",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["msg"] == "hello"
    assert data["session_id"] == "s1"
    assert data["placeholder"] is True
    assert data["turn_count"] == 1


def test_post_ask_bot_missing_msg(client: TestClient) -> None:
    resp = client.post(
        "/ask_bot",
        content=b"session_id=s1",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 422


def test_post_ask_bot_missing_session_id(client: TestClient) -> None:
    resp = client.post(
        "/ask_bot",
        content=b"msg=hello",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 422


def test_post_ask_bot_whitespace_msg(client: TestClient) -> None:
    resp = client.post(
        "/ask_bot",
        content=b"msg=+++&session_id=s1",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 422


def test_post_ask_bot_empty_body(client: TestClient) -> None:
    resp = client.post(
        "/ask_bot",
        content=b"",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 422


def test_post_ask_bot_json_unsupported(client: TestClient) -> None:
    resp = client.post(
        "/ask_bot",
        json={"msg": "hello", "session_id": "s1"},
    )
    assert resp.status_code == 415


def test_openapi_json_contains_paths(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    openapi = resp.json()
    paths = openapi.get("paths", {})
    assert "/" in paths
    assert "/health" in paths
    assert "/chat" in paths
    assert "/ask_bot" in paths
    get_home = paths["/"].get("get", {})
    assert get_home.get("summary") == "Home"
    get_health = paths["/health"].get("get", {})
    assert get_health.get("summary") == "Health"
    post_chat = paths["/chat"].get("post", {})
    assert post_chat.get("summary") == "Chat"
    post_ask = paths["/ask_bot"].get("post", {})
    assert post_ask.get("summary") == "Ask Bot"


def test_session_memory_isolation(client: TestClient) -> None:
    r1 = client.post("/chat", json={"msg": "a", "session_id": "alpha"})
    r2 = client.post("/chat", json={"msg": "b", "session_id": "beta"})
    assert r1.json()["turn_count"] == 1
    assert r2.json()["turn_count"] == 1
    alpha = session_messages_copy("alpha")
    beta = session_messages_copy("beta")
    assert alpha == [("user", "a"), ("assistant", "a")]
    assert beta == [("user", "b"), ("assistant", "b")]


def test_session_memory_continuity(client: TestClient) -> None:
    first = client.post("/chat", json={"msg": "one", "session_id": "s-cont"})
    second = client.post("/chat", json={"msg": "two", "session_id": "s-cont"})
    assert first.json()["turn_count"] == 1
    assert second.json()["turn_count"] == 2
    assert session_messages_copy("s-cont") == [
        ("user", "one"),
        ("assistant", "one"),
        ("user", "two"),
        ("assistant", "two"),
    ]


def test_session_memory_cross_endpoint_parity(client: TestClient) -> None:
    r_chat = client.post("/chat", json={"msg": "from_json", "session_id": "s-par"})
    assert r_chat.json()["turn_count"] == 1
    r_form = client.post(
        "/ask_bot",
        content=b"msg=from_form&session_id=s-par",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert r_form.json()["turn_count"] == 2
    assert session_messages_copy("s-par") == [
        ("user", "from_json"),
        ("assistant", "from_json"),
        ("user", "from_form"),
        ("assistant", "from_form"),
    ]


def test_chat_memory_max_turns_trims(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setenv("CHAT_MEMORY_MAX_TURNS", "2")
    for i in range(3):
        client.post("/chat", json={"msg": str(i), "session_id": "s-max"})
    assert session_messages_copy("s-max") == [
        ("user", "1"),
        ("assistant", "1"),
        ("user", "2"),
        ("assistant", "2"),
    ]


def test_session_memory_case_sensitive_keys(client: TestClient) -> None:
    client.post("/chat", json={"msg": "x", "session_id": "Sid"})
    client.post("/chat", json={"msg": "y", "session_id": "sid"})
    assert session_messages_copy("Sid") == [("user", "x"), ("assistant", "x")]
    assert session_messages_copy("sid") == [("user", "y"), ("assistant", "y")]


def test_invalid_chat_does_not_write_session_memory(client: TestClient) -> None:
    client.post("/chat", json={"msg": "ok", "session_id": "s-inv"})
    bad = client.post("/chat", json={"msg": "   ", "session_id": "s-inv"})
    assert bad.status_code == 422
    assert session_messages_copy("s-inv") == [
        ("user", "ok"),
        ("assistant", "ok"),
    ]

    bad_ct = client.post(
        "/chat",
        content=b"msg=hello&session_id=s-inv",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert bad_ct.status_code == 422
    assert len(session_messages_copy("s-inv")) == 2


def test_invalid_ask_bot_does_not_write_session_memory(client: TestClient) -> None:
    client.post(
        "/ask_bot",
        content=b"msg=ok&session_id=s-ab",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    bad415 = client.post(
        "/ask_bot",
        json={"msg": "nope", "session_id": "s-ab"},
    )
    assert bad415.status_code == 415
    assert session_messages_copy("s-ab") == [
        ("user", "ok"),
        ("assistant", "ok"),
    ]

    bad422 = client.post(
        "/ask_bot",
        content=b"",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert bad422.status_code == 422
    assert len(session_messages_copy("s-ab")) == 2
