"""Central LLM call for the clinic chatbot (VE-20, VE-24).

FastAPI handlers for ``POST /chat`` and ``POST /ask_bot`` delegate to
:func:`invoke_chat_llm` so OpenAI credentials and prompt loading stay in one
place.

Tools (VE-24): mock Tetris availability (VE-23) and Google Calendar read-only
listing are bound on the chat model; the server runs a short tool-calling loop
until the model returns a plain text reply.

The base system instructions are read from ``prompt.md`` in the repository
root (same directory as ``main.py`` and this module):
``Path(__file__).resolve().parent / "prompt.md"``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from availability_mock_tool import mock_tetris_booking_tools
from conversation_memory import session_messages_copy
from google_calendar_tool import google_calendar_tools, safe_json_for_tool_message

logger = logging.getLogger(__name__)

# Repo root-relative file (this module lives next to main.py).
SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompt.md"

_MAX_TOOL_ROUNDS = 10


class LlmConfigurationError(Exception):
    """API key or ``prompt.md`` is missing, empty, or unusable."""


class LlmUpstreamError(Exception):
    """The LLM provider failed or returned unusable output."""


def load_system_prompt() -> str:
    """Load and validate the markdown system prompt from ``prompt.md``.

    :return: Non-empty stripped system prompt text.
    :raises LlmConfigurationError: If the file is missing or empty.
    """
    if not SYSTEM_PROMPT_FILE.is_file():
        raise LlmConfigurationError(
            "System prompt file is missing (expected prompt.md next to main.py)."
        )
    raw = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    if not raw.strip():
        raise LlmConfigurationError(
            "System prompt file is empty or whitespace-only."
        )
    return raw.strip()


def _require_openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise LlmConfigurationError(
            "OPENAI_API_KEY is not set or empty; configure the environment."
        )
    return key


def _chat_model_name() -> str:
    name = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini").strip()
    return name or "gpt-4o-mini"


def _chat_tools() -> list:
    return [*mock_tetris_booking_tools(), *google_calendar_tools()]


def _extract_text_content(message: AIMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts).strip()
    return ""


async def invoke_chat_llm(
    user_message: str,
    session_id: str | None = None,
) -> str:
    """Run a user turn with optional session history and tool calling.

    Reads ``OPENAI_API_KEY`` from the environment only. Does not log secrets.

    :param user_message: Validated user text (non-empty).
    :param session_id: When set, prior turns from memory precede this message.
    :return: Assistant reply text.
    :raises LlmConfigurationError: Misconfiguration (key or prompt).
    :raises LlmUpstreamError: Provider or empty model output.
    """
    system_text = load_system_prompt()
    api_key = _require_openai_api_key()
    tools = _chat_tools()
    tool_by_name = {t.name: t for t in tools}
    model = ChatOpenAI(
        api_key=api_key,
        model=_chat_model_name(),
        temperature=0.2,
    )
    bound = model.bind_tools(tools)

    messages: list = [SystemMessage(content=system_text)]
    if session_id is not None:
        for role, text in session_messages_copy(session_id):
            if role == "user":
                messages.append(HumanMessage(content=text))
            else:
                messages.append(AIMessage(content=text))
    messages.append(HumanMessage(content=user_message))

    try:
        for _ in range(_MAX_TOOL_ROUNDS):
            result = await bound.ainvoke(messages)
            if not isinstance(result, AIMessage):
                raise LlmUpstreamError(
                    "The assistant returned an unexpected response type."
                )
            messages.append(result)
            tool_calls = getattr(result, "tool_calls", None) or []
            if not tool_calls:
                text = _extract_text_content(result)
                if not text:
                    raise LlmUpstreamError(
                        "The assistant returned an empty response."
                    )
                return text
            for call in tool_calls:
                if isinstance(call, dict):
                    name = str(call.get("name", "") or "")
                    args = call.get("args", {}) or {}
                    tid = str(call.get("id", "") or "")
                else:
                    name = str(getattr(call, "name", "") or "")
                    args = getattr(call, "args", {}) or {}
                    tid = str(getattr(call, "id", "") or "")
                tool_obj = tool_by_name.get(name)
                if tool_obj is None:
                    payload = {
                        "ok": False,
                        "error": {"code": "UNKNOWN_TOOL", "message": name},
                    }
                else:
                    try:
                        payload = tool_obj.invoke(args)
                    except Exception:
                        logger.exception("Tool invocation failed (%s)", name)
                        payload = {
                            "ok": False,
                            "error": {
                                "code": "TOOL_EXCEPTION",
                                "message": "Tool execution failed.",
                            },
                        }
                messages.append(
                    ToolMessage(
                        content=safe_json_for_tool_message(payload),
                        tool_call_id=tid,
                    )
                )
    except LlmUpstreamError:
        raise
    except Exception as exc:
        logger.error("LLM provider call failed (%s)", type(exc).__name__)
        raise LlmUpstreamError(
            "The assistant is temporarily unavailable. Please try again later."
        ) from None

    raise LlmUpstreamError(
        "The assistant stopped after too many tool calls; please try again."
    )
