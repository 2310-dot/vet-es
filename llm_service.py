"""Central LLM call for the clinic chatbot (VE-20, VE-25).

FastAPI handlers delegate to :func:`invoke_chat_llm` or :data:`clinic_chat` so
OpenAI credentials and prompt loading stay in one place.

VE-25: **tool-free** conversational path only — ``ChatOpenAI`` with message
history from :mod:`conversation_memory`. No ``bind_tools``, no agents.

The base system instructions are read from ``prompt.md`` in the repository
root (same directory as ``main.py`` and this module):
``Path(__file__).resolve().parent / "prompt.md"``.

:class:`ClinicChat` exposes ``await clinic_chat.ainvoke(input, config)`` where
``config`` is ``{"configurable": {"session_id": "<id>"}}``; the return value is
an :class:`~langchain_core.messages.AIMessage` with a string ``.content``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from conversation_memory import session_messages_copy

logger = logging.getLogger(__name__)

# Repo root-relative file (this module lives next to main.py).
SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompt.md"


class LlmConfigurationError(Exception):
    """API key or ``prompt.md`` is missing, empty, or unusable."""


class LlmUpstreamError(Exception):
    """The LLM provider failed or returned unusable output."""


class ClinicChat:
    """Runnable-style entry point for HTTP layers (VE-25).

    ``await clinic_chat.ainvoke(user_text, config)`` returns an ``AIMessage``
    whose ``content`` is the assistant reply string.
    """

    async def ainvoke(self, input: str, config: dict | None = None) -> AIMessage:
        """Run one user turn; ``config["configurable"]["session_id"]`` keys history."""
        cfg = config or {}
        configurable = cfg.get("configurable") or {}
        raw_sid = configurable.get("session_id")
        session_id: str | None
        if raw_sid is None:
            session_id = None
        else:
            session_id = str(raw_sid).strip() or None
        text = await invoke_chat_llm(input, session_id)
        return AIMessage(content=text)

    async def invoke(self, input: str, config: dict | None = None) -> AIMessage:
        """Alias for :meth:`ainvoke` (async API)."""
        return await self.ainvoke(input, config)


clinic_chat = ClinicChat()


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


def _llm_debug_errors_enabled() -> bool:
    """When true, :exc:`LlmUpstreamError` includes the underlying exception."""
    return os.environ.get("LLM_DEBUG_ERRORS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


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
    """Run a user turn with optional session history (no tools).

    Reads ``OPENAI_API_KEY`` from the environment only. Does not log secrets.

    :param user_message: Validated user text (non-empty).
    :param session_id: When set, prior turns from memory precede this message.
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

    messages: list = [SystemMessage(content=system_text)]
    if session_id is not None:
        for role, text in session_messages_copy(session_id):
            if role == "user":
                messages.append(HumanMessage(content=text))
            else:
                messages.append(AIMessage(content=text))
    messages.append(HumanMessage(content=user_message))

    try:
        result = await model.ainvoke(messages)
        if not isinstance(result, AIMessage):
            raise LlmUpstreamError(
                "The assistant returned an unexpected response type."
            )
        text = _extract_text_content(result)
        if not text:
            raise LlmUpstreamError("The assistant returned an empty response.")
        return text
    except LlmUpstreamError:
        raise
    except Exception as exc:
        logger.exception("LLM provider failed")
        if _llm_debug_errors_enabled():
            raise LlmUpstreamError(f"{type(exc).__name__}: {exc}") from exc
        raise LlmUpstreamError(
            "The assistant is temporarily unavailable. Please try again later."
        ) from None
