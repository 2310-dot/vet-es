"""Unit tests for llm_service (VE-20)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest

from llm_service import (
    LlmConfigurationError,
    LlmUpstreamError,
    invoke_chat_llm,
    load_system_prompt,
)


def test_load_system_prompt_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "prompt.md"
    empty.write_text("   \n\t  ", encoding="utf-8")
    with patch("llm_service.SYSTEM_PROMPT_FILE", empty):
        with pytest.raises(LlmConfigurationError, match="empty or whitespace"):
            load_system_prompt()


def test_invoke_chat_llm_maps_provider_exception() -> None:
    async def boom(*_a, **_kw):
        raise RuntimeError("simulated network failure")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.ChatOpenAI") as mock_cls:
            instance = mock_cls.return_value
            instance.ainvoke = boom

            with pytest.raises(LlmUpstreamError, match="temporarily unavailable"):
                asyncio.run(invoke_chat_llm("hi"))

    mock_cls.assert_called_once()


def test_invoke_chat_llm_rejects_empty_model_content() -> None:
    from langchain_core.messages import AIMessage

    async def empty_reply(*_a, **_kw):
        return AIMessage(content="")

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with patch("llm_service.ChatOpenAI") as mock_cls:
            instance = mock_cls.return_value
            instance.ainvoke = empty_reply

            with pytest.raises(LlmUpstreamError, match="empty response"):
                asyncio.run(invoke_chat_llm("hi"))

