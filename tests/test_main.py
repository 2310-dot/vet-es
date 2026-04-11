"""Tests for main.py: Chatbot v4 placeholder API (VETES-16, VE-18, VE-19)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


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
