"""Tests for main.py: FastAPI chatbot API (VE-18, VE-19, VE-20, VE-21)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from conversation_memory import reset_chat_memory_for_tests, session_messages_copy
from llm_service import LlmUpstreamError
from main import app


def _session_cfg(session_id: str) -> dict:
    return {"configurable": {"session_id": session_id}}


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
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="assistant reply")
        resp = client.post(
            "/chat",
            json={"msg": "  hello  ", "session_id": "s1"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["msg"] == "assistant reply"
    assert data["session_id"] == "s1"
    assert data["placeholder"] is False
    assert data["turn_count"] == 1
    mock_llm.assert_awaited_once_with("hello", _session_cfg("s1"))


def test_post_chat_invokes_central_llm_function(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="ok")
        client.post(
            "/chat",
            json={"msg": "user text", "session_id": "sid"},
        )
    mock_llm.assert_awaited_once_with("user text", _session_cfg("sid"))


def test_post_chat_missing_openai_key_503(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post(
        "/chat",
        json={"msg": "hello", "session_id": "s1"},
    )
    assert resp.status_code == 503
    assert "OPENAI_API_KEY" in resp.json()["detail"]


def test_post_chat_upstream_error_502(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = LlmUpstreamError("upstream down")
        resp = client.post(
            "/chat",
            json={"msg": "hello", "session_id": "s1"},
        )
    assert resp.status_code == 502
    assert resp.json()["detail"] == "upstream down"


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
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="form assistant reply")
        resp = client.post(
            "/ask_bot",
            content=b"msg=hello&session_id=s1",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["msg"] == "form assistant reply"
    assert data["session_id"] == "s1"
    assert data["placeholder"] is False
    assert data["turn_count"] == 1
    mock_llm.assert_awaited_once_with("hello", _session_cfg("s1"))


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
    assert "/askbot" in paths
    public_paths = [p for p in paths if p.startswith("/public")]
    assert public_paths, "expected a /public/... route in OpenAPI paths"
    get_home = paths["/"].get("get", {})
    assert get_home.get("summary") == "Home"
    get_health = paths["/health"].get("get", {})
    assert get_health.get("summary") == "Health"
    post_chat = paths["/chat"].get("post", {})
    assert post_chat.get("summary") == "Chat"
    post_ask = paths["/ask_bot"].get("post", {})
    assert post_ask.get("summary") == "Ask Bot"
    post_askbot = paths["/askbot"].get("post", {})
    assert post_askbot.get("summary") == "Ask bot (VE-25)"


def test_get_public_welcome_ok(client: TestClient) -> None:
    """VE-25: existing file under public/ is served with 200."""
    resp = client.get("/public/welcome.txt")
    assert resp.status_code == 200
    assert "Welcome to the vet-es public" in resp.text


def test_get_public_path_traversal_blocked(client: TestClient) -> None:
    """VE-25: paths escaping public/ return 404."""
    resp = client.get("/public/../main.py")
    assert resp.status_code == 404


def test_get_public_missing_file_404(client: TestClient) -> None:
    resp = client.get("/public/does-not-exist-ve25.bin")
    assert resp.status_code == 404


def test_post_askbot_json_ok(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="askbot json reply")
        resp = client.post(
            "/askbot",
            json={"msg": "hi", "session_id": "s-ask"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["msg"] == "askbot json reply"
    assert data["session_id"] == "s-ask"
    mock_llm.assert_awaited_once_with("hi", _session_cfg("s-ask"))


def test_post_askbot_urlencoded_ok(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="askbot form reply")
        resp = client.post(
            "/askbot",
            content=b"msg=hello&session_id=s-form",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    assert resp.json()["msg"] == "askbot form reply"
    mock_llm.assert_awaited_once_with("hello", _session_cfg("s-form"))


def test_post_askbot_missing_fields_422(client: TestClient) -> None:
    resp = client.post(
        "/askbot",
        json={"msg": "", "session_id": "s1"},
    )
    assert resp.status_code == 422
    resp2 = client.post(
        "/askbot",
        json={"msg": "x", "session_id": "  "},
    )
    assert resp2.status_code == 422


def test_post_askbot_unsupported_media_type_415(client: TestClient) -> None:
    resp = client.post(
        "/askbot",
        content=b"{}",
        headers={"content-type": "text/plain"},
    )
    assert resp.status_code == 415


def test_post_askbot_session_memory_continuity(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [
            AIMessage(content="first"),
            AIMessage(content="second"),
        ]
        client.post(
            "/askbot",
            json={"msg": "one", "session_id": "s-askbot-cont"},
        )
        client.post(
            "/askbot",
            json={"msg": "two", "session_id": "s-askbot-cont"},
        )
    hist = session_messages_copy("s-askbot-cont")
    assert hist == [
        ("user", "one"),
        ("assistant", "first"),
        ("user", "two"),
        ("assistant", "second"),
    ]
    assert mock_llm.await_count == 2


# ---------- VE-21: session memory tests ----------

def test_session_memory_isolation(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [AIMessage(content="a"), AIMessage(content="b")]
        r1 = client.post("/chat", json={"msg": "a", "session_id": "alpha"})
        r2 = client.post("/chat", json={"msg": "b", "session_id": "beta"})
    assert r1.json()["turn_count"] == 1
    assert r2.json()["turn_count"] == 1
    assert session_messages_copy("alpha") == [("user", "a"), ("assistant", "a")]
    assert session_messages_copy("beta") == [("user", "b"), ("assistant", "b")]


def test_session_memory_continuity(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [
            AIMessage(content="one"),
            AIMessage(content="two"),
        ]
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
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [
            AIMessage(content="from_json"),
            AIMessage(content="from_form"),
        ]
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
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [
            AIMessage(content="0"),
            AIMessage(content="1"),
            AIMessage(content="2"),
        ]
        for i in range(3):
            client.post("/chat", json={"msg": str(i), "session_id": "s-max"})
    assert session_messages_copy("s-max") == [
        ("user", "1"),
        ("assistant", "1"),
        ("user", "2"),
        ("assistant", "2"),
    ]


def test_session_memory_case_sensitive_keys(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [AIMessage(content="x"), AIMessage(content="y")]
        client.post("/chat", json={"msg": "x", "session_id": "Sid"})
        client.post("/chat", json={"msg": "y", "session_id": "sid"})
    assert session_messages_copy("Sid") == [("user", "x"), ("assistant", "x")]
    assert session_messages_copy("sid") == [("user", "y"), ("assistant", "y")]


def test_invalid_chat_does_not_write_session_memory(client: TestClient) -> None:
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="ok")
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
    with patch("main.clinic_chat.ainvoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = AIMessage(content="ok")
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


# ---------- VE-20: system prompt loading ----------

def test_invoke_chat_llm_uses_system_prompt_from_file() -> None:
    """Outbound messages include system text loaded from prompt.md (VE-20 AC7)."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    import llm_service
    from llm_service import invoke_chat_llm

    system_text = llm_service.load_system_prompt()
    assert "must not diagnose" in system_text.lower()

    captured: list = []

    async def fake_ainvoke(messages):
        captured.extend(messages)
        return AIMessage(content="stub")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"}):
        with patch("llm_service.ChatOpenAI") as mock_cls:
            instance = mock_cls.return_value
            instance.ainvoke = fake_ainvoke
            result = asyncio.run(invoke_chat_llm("user question"))

    assert result == "stub"
    assert len(captured) == 2
    assert isinstance(captured[0], SystemMessage)
    assert captured[0].content == system_text
    assert isinstance(captured[1], HumanMessage)
    assert captured[1].content == "user question"
