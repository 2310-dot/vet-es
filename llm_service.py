"""Central LLM call for the clinic chatbot (VE-20).

FastAPI handlers for ``POST /chat`` and ``POST /ask_bot`` delegate to
:func:`invoke_chat_llm` so OpenAI credentials and prompt loading stay in one
place.

The base system instructions are read from ``prompt.md`` in the repository
root (same directory as ``main.py`` and this module):
``Path(__file__).resolve().parent / "prompt.md"``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Repo root-relative file (this module lives next to main.py).
SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompt.md"


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


async def invoke_chat_llm(user_message: str) -> str:
    """Run a single user turn against the chat model (system + user messages).

    Reads ``OPENAI_API_KEY`` from the environment only. Does not log secrets.

    :param user_message: Validated user text (non-empty).
    :return: Assistant reply text.
    :raises LlmConfigurationError: Misconfiguration (key or prompt).
    :raises LlmUpstreamError: Provider or empty model output.
    """
    system_text = load_system_prompt()
    api_key = _require_openai_api_key()
    model = ChatOpenAI(
        api_key=api_key,
        model=_chat_model_name(),
        temperature=0.2,
    )
    try:
        result = await model.ainvoke(
            [
                SystemMessage(content=system_text),
                HumanMessage(content=user_message),
            ]
        )
    except Exception as exc:
        # Do not log request headers or exception strings that may contain PII.
        logger.error("LLM provider call failed (%s)", type(exc).__name__)
        raise LlmUpstreamError(
            "The assistant is temporarily unavailable. Please try again later."
        ) from None

    if not isinstance(result, AIMessage):
        raise LlmUpstreamError(
            "The assistant returned an unexpected response type."
        )
    text = _extract_text_content(result)
    if not text:
        raise LlmUpstreamError("The assistant returned an empty response.")
    return text
