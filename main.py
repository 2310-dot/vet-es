"""Clinic chatbot API: Chatbot v4 (GET / HTML, POST /ask_bot form); plus /health and POST /chat."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from conversation_memory import record_exchange, session_messages_copy
from llm_service import (
    LlmConfigurationError,
    LlmUpstreamError,
    invoke_chat_llm,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Chatbot v4",
    version="0.1.0",
    description=(
        "Chatbot v4 OpenAPI: GET / (HTML), POST /ask_bot (application/x-www-form-urlencoded). "
        "Extensions: GET /health, POST /chat (JSON), static /static. "
        "LLM via llm_service where configured."
    ),
)


def _maybe_add_cors(application: FastAPI) -> None:
    """Enable CORS when CORS_ALLOW_ORIGINS is set (comma-separated origins)."""
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        return
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )


_maybe_add_cors(app)


class HealthResponse(BaseModel):
    """JSON body for GET /health."""

    status: str = Field(examples=["ok"])


class ChatRequest(BaseModel):
    """JSON body for POST /chat."""

    msg: str = Field(examples=["hello"])
    session_id: str = Field(examples=["s1"])

    @field_validator("msg", "session_id")
    @classmethod
    def strip_and_require_non_empty(cls, value: str) -> str:
        """Strip whitespace; reject empty or whitespace-only strings."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty or whitespace-only")
        return cleaned


class AskBotResponse(BaseModel):
    """Assistant reply for POST /chat and POST /ask_bot."""

    msg: str = Field(
        description="Assistant reply text.",
        examples=["We are open Monday–Friday 9–18. How can I help?"],
    )
    session_id: str = Field(examples=["s1"])
    placeholder: bool = Field(
        default=False,
        description="Reserved for stub responses; false when the LLM produced msg.",
    )
    turn_count: int = Field(
        default=0,
        ge=0,
        description="Completed user→assistant pairs stored for this session after this request.",
        examples=[1],
    )


@app.get(
    "/",
    summary="Home",
    operation_id="home_get",
    response_class=Response,
    responses={200: {"content": {"text/html": {}}}},
)
async def home() -> Response:
    """Serve minimal HTML+JS chat demo (VE-19)."""
    html_path = STATIC_DIR / "chat.html"
    if not html_path.is_file():
        fallback = (
            "<!DOCTYPE html><html><head><title>Chatbot v4</title></head>"
            "<body><h1>Chatbot v4</h1><p>static/chat.html is missing.</p></body></html>"
        )
        return Response(content=fallback, media_type="text/html")
    html = html_path.read_text(encoding="utf-8")
    return Response(content=html, media_type="text/html")


@app.get(
    "/health",
    summary="Health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    """Liveness check for load balancers and monitoring."""
    return HealthResponse(status="ok")


async def _assistant_reply(user_text: str, session_id: str) -> AskBotResponse:
    """Call the central LLM entrypoint, record the exchange in memory, and map errors to HTTP responses."""
    try:
        reply = await invoke_chat_llm(user_text, session_id)
    except LlmConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    turn_count = record_exchange(session_id, user_text, reply)
    return AskBotResponse(
        msg=reply,
        session_id=session_id,
        placeholder=False,
        turn_count=turn_count,
    )


@app.post(
    "/chat",
    summary="Chat",
    response_model=AskBotResponse,
)
async def chat(body: ChatRequest) -> AskBotResponse:
    """JSON chat: delegates to :func:`llm_service.invoke_chat_llm` and records memory."""
    return await _assistant_reply(body.msg, body.session_id)


def _parse_urlencoded_body(body_bytes: bytes) -> dict[str, str]:
    parsed = parse_qs(body_bytes.decode("utf-8"), keep_blank_values=True)
    flat: dict[str, str] = {}
    for key, values in parsed.items():
        if values:
            flat[key] = values[-1]
    return flat


def _resolve_ask_bot_form_fields(body_bytes: bytes) -> tuple[str, str]:
    """Parse urlencoded body; apply Chatbot v4 defaults for missing keys.

    OpenAPI defaults: ``msg`` → ``''``, ``session_id`` → ``'default'``.
    Empty or whitespace-only ``session_id`` is normalized to ``'default'``.

    :param body_bytes: Raw body; may be empty when all defaults apply.
    :return: ``(msg, session_id)`` as stored in the form (msg not stripped).
    """
    if not body_bytes.strip():
        return "", "default"
    fields = _parse_urlencoded_body(body_bytes)
    msg = fields.get("msg", "")
    session_raw = fields.get("session_id", "default")
    session_clean = session_raw.strip()
    if not session_clean:
        session_clean = "default"
    return msg, session_clean


_EMPTY_MSG_REPLY = "Please enter a message."


@app.post(
    "/ask_bot",
    summary="Ask Bot",
    operation_id="ask_bot_ask_bot_post",
    response_model=AskBotResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "msg": {"type": "string", "default": "", "title": "Msg"},
                            "session_id": {
                                "type": "string",
                                "default": "default",
                                "title": "Session Id",
                            },
                        },
                    }
                }
            }
        }
    },
)
async def ask_bot(request: Request) -> AskBotResponse:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" not in content_type:
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/x-www-form-urlencoded",
        )
    body_bytes = await request.body()
    msg, session_id = _resolve_ask_bot_form_fields(body_bytes)
    msg_clean = msg.strip()
    if not msg_clean:
        turn_count = len(session_messages_copy(session_id)) // 2
        return AskBotResponse(
            msg=_EMPTY_MSG_REPLY,
            session_id=session_id,
            placeholder=True,
            turn_count=turn_count,
        )
    return await _assistant_reply(msg_clean, session_id)


if STATIC_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )
