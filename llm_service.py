"""Central LLM call for the clinic chatbot (VE-20, VE-25, VE-28, VE-29, VE-30).

FastAPI handlers delegate to :func:`invoke_chat_llm` or :data:`clinic_chat` so
OpenAI credentials and prompt loading stay in one place.

VE-28: When the pre-op index is loaded, retrieved chunks from the official
pre-operative URL are appended to the system prompt before the model call.

VE-25: Conversational path with session history from :mod:`conversation_memory`.

VE-29 / VE-30: The chat model binds ``check_surgical_availability`` (orientative
theatre availability: mock table or Google Calendar when configured). Tool
results are appended and the model is re-invoked until it returns a final text
reply.

The long system prompt is **not** inlined in Python. It is read at runtime from
``prompt.md`` in the repository root (next to ``main.py``). The brief pointer
:data:`SYSTEM_PROMPT_SOURCE_REF` documents that the definitive advanced prompt
for the ENAE case lives in course deliverables and that ``prompt.md`` is the
in-repo working copy to keep aligned.

:class:`ClinicChat` exposes ``await clinic_chat.ainvoke(input, config)`` where
``config`` is ``{"configurable": {"session_id": "<id>"}}``; the return value is
an :class:`~langchain_core.messages.AIMessage` with a string ``.content``.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from conversation_memory import session_messages_copy
from tools.availability import check_surgical_availability
from preop_rag.pipeline import retrieve_top_k
from preop_rag.runtime import (
    PREOP_SOURCE_UNAVAILABLE_USER_MESSAGE,
    get_preop_top_k,
    get_preop_vector_store,
    looks_like_preoperative_question,
    preop_source_fetch_failed,
)

logger = logging.getLogger(__name__)

CLINIC_TOOLS: list[BaseTool] = [check_surgical_availability]
_MAX_TOOL_ROUNDS = 8

# Repo root-relative file (this module lives next to main.py).
SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent / "prompt.md"

# Placeholder / pointer only (ticket AC): do not paste the full advanced prompt here.
# Runtime instructions are loaded from ``SYSTEM_PROMPT_FILE``; keep that file aligned
# with the canonical prompt in the ENAE case course materials.
SYSTEM_PROMPT_SOURCE_REF = (
    "Definitive advanced system prompt: ENAE case course deliverables. "
    "Working copy for this API: prompt.md (repository root, next to main.py), loaded at runtime."
)


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

    See :data:`SYSTEM_PROMPT_SOURCE_REF` for the documented split between course
    materials (canonical advanced prompt) and this file (operational copy).

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


def _tools_by_name() -> dict[str, BaseTool]:
    return {tool.name: tool for tool in CLINIC_TOOLS}


async def _invoke_until_text_reply(
    model: ChatOpenAI,
    messages: list,
) -> str:
    """Run ``model`` with tools bound; loop on tool calls until text output."""
    model_with_tools = model.bind_tools(CLINIC_TOOLS)
    lookup = _tools_by_name()
    for _ in range(_MAX_TOOL_ROUNDS):
        result = await model_with_tools.ainvoke(messages)
        if not isinstance(result, AIMessage):
            raise LlmUpstreamError(
                "The assistant returned an unexpected response type."
            )
        tool_calls = getattr(result, "tool_calls", None) or []
        if not tool_calls:
            text = _extract_text_content(result)
            if not text:
                raise LlmUpstreamError("The assistant returned an empty response.")
            return text

        messages.append(result)
        for tc in tool_calls:
            if isinstance(tc, dict):
                name = tc.get("name") or ""
                tool_call_id = tc.get("id") or ""
                raw_args = tc.get("args")
            else:
                name = getattr(tc, "name", "") or ""
                tool_call_id = getattr(tc, "id", "") or ""
                raw_args = getattr(tc, "args", None)
            args = raw_args if isinstance(raw_args, dict) else {}
            tool = lookup.get(name)
            if tool is None:
                payload: dict[str, Any] = {"error": f"Unknown tool: {name}"}
            else:
                try:
                    raw = tool.invoke(args)
                    payload = raw if isinstance(raw, dict) else {"result": raw}
                except Exception:
                    logger.exception("Tool invocation failed (name=%s)", name)
                    payload = {
                        "error": "TOOL_FAILED",
                        "message": "Tool execution failed; try again or rephrase.",
                    }
            messages.append(
                ToolMessage(
                    content=json.dumps(payload, ensure_ascii=False),
                    tool_call_id=tool_call_id,
                )
            )
    raise LlmUpstreamError(
        "The assistant stopped after too many tool calls; please try again."
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
    if preop_source_fetch_failed() and looks_like_preoperative_question(user_message):
        return PREOP_SOURCE_UNAVAILABLE_USER_MESSAGE

    system_text = load_system_prompt()
    store = get_preop_vector_store()
    if store is not None:
        try:
            docs = retrieve_top_k(store, user_message, k=get_preop_top_k())
        except Exception:
            logger.exception("Pre-op RAG retrieval failed; continuing without excerpts")
            docs = []
        if docs:
            parts = [
                f"[Excerpt {i}]\n{doc.page_content.strip()}"
                for i, doc in enumerate(docs, start=1)
            ]
            block = "\n\n".join(parts)
            system_text = (
                f"{system_text}\n\n"
                f"--- Retrieved pre-operative reference excerpts ---\n"
                f"{block}\n"
                f"--- End excerpts ---"
            )

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
        return await _invoke_until_text_reply(model, messages)
    except LlmUpstreamError:
        raise
    except Exception as exc:
        logger.exception("LLM provider failed")
        if _llm_debug_errors_enabled():
            raise LlmUpstreamError(f"{type(exc).__name__}: {exc}") from exc
        raise LlmUpstreamError(
            "The assistant is temporarily unavailable. Please try again later."
        ) from None
