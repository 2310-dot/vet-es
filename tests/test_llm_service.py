"""Unit tests for llm_service (VE-20, VE-25)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.vectorstores import InMemoryVectorStore

from llm_service import (
    LlmConfigurationError,
    LlmUpstreamError,
    invoke_chat_llm,
    load_system_prompt,
)
from preop_rag.runtime import PREOP_SOURCE_UNAVAILABLE_USER_MESSAGE


def test_load_system_prompt_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "prompt.md"
    empty.write_text("   \n\t  ", encoding="utf-8")
    with patch("llm_service.SYSTEM_PROMPT_FILE", empty):
        with pytest.raises(LlmConfigurationError, match="empty or whitespace"):
            load_system_prompt()


def _chat_instance_with_bind(mock_cls: MagicMock) -> MagicMock:
    instance = mock_cls.return_value
    instance.bind_tools = MagicMock(return_value=instance)
    return instance


def test_invoke_chat_llm_maps_provider_exception() -> None:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.ChatOpenAI") as mock_cls:
            instance = _chat_instance_with_bind(mock_cls)
            instance.ainvoke = AsyncMock(
                side_effect=RuntimeError("simulated network failure")
            )

            with pytest.raises(LlmUpstreamError, match="temporarily unavailable"):
                asyncio.run(invoke_chat_llm("hi"))

    mock_cls.assert_called_once()


def test_invoke_chat_llm_rejects_empty_model_content() -> None:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.ChatOpenAI") as mock_cls:
            instance = _chat_instance_with_bind(mock_cls)
            instance.ainvoke = AsyncMock(return_value=AIMessage(content=""))

            with pytest.raises(LlmUpstreamError, match="empty response"):
                asyncio.run(invoke_chat_llm("hi"))


def test_invoke_chat_llm_preop_fetch_failed_returns_configured_spanish_message() -> None:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.preop_source_fetch_failed", return_value=True):
            with patch("llm_service.looks_like_preoperative_question", return_value=True):
                out = asyncio.run(
                    invoke_chat_llm("¿Cuántas horas de ayuno antes de la operación?")
                )
    assert out == PREOP_SOURCE_UNAVAILABLE_USER_MESSAGE


def test_invoke_chat_llm_appends_preop_excerpts_when_index_loaded() -> None:
    store = InMemoryVectorStore.from_documents(
        [
            Document(
                page_content=(
                    "Official instruction: fast twelve hours; water until two hours before."
                ),
                metadata={},
            )
        ],
        FakeEmbeddings(size=1536),
    )
    captured: list = []

    async def fake_ainvoke(messages):
        captured.extend(messages)
        return AIMessage(content="stub")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.preop_source_fetch_failed", return_value=False):
            with patch("llm_service.get_preop_vector_store", return_value=store):
                with patch("llm_service.ChatOpenAI") as mock_cls:
                    instance = _chat_instance_with_bind(mock_cls)
                    instance.ainvoke = fake_ainvoke
                    asyncio.run(invoke_chat_llm("fasting before surgery"))

    assert captured
    system_text = captured[0].content
    assert isinstance(system_text, str)
    assert "Retrieved pre-operative reference excerpts" in system_text
    assert "twelve hours" in system_text


def test_invoke_chat_llm_uses_system_prompt_from_file() -> None:
    """Outbound messages include system text loaded from prompt.md (VE-20 AC7)."""
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
            instance = _chat_instance_with_bind(mock_cls)
            instance.ainvoke = fake_ainvoke
            result = asyncio.run(invoke_chat_llm("user question"))

    assert result == "stub"
    assert len(captured) == 2
    assert isinstance(captured[0], SystemMessage)
    assert captured[0].content == system_text
    assert isinstance(captured[1], HumanMessage)
    assert captured[1].content == "user question"


def test_invoke_chat_llm_executes_tool_then_returns_text() -> None:
    """VE-29: model may emit tool_calls; service runs tool and re-invokes."""
    calls: list[int] = []

    async def fake_ainvoke(messages):
        calls.append(len(messages))
        if len(calls) == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "check_surgical_availability",
                        "args": {"date": "2026-04-14"},
                        "id": "call_tc1",
                    }
                ],
            )
        return AIMessage(
            content="Orientative availability only; contact the clinic to confirm."
        )

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.ChatOpenAI") as mock_cls:
            instance = _chat_instance_with_bind(mock_cls)
            instance.ainvoke = fake_ainvoke
            out = asyncio.run(
                invoke_chat_llm("Is there theatre space next Tuesday?")
            )

    assert out.startswith("Orientative")
    assert len(calls) == 2
    assert calls[1] > calls[0]

