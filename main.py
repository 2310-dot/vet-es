"""Clinic chatbot API: HTML demo, health, chat, ask_bot, VE-25 ``/public`` and ``/askbot``."""

from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.responses import FileResponse

from conversation_memory import record_exchange
from llm_service import (
    LlmConfigurationError,
    LlmUpstreamError,
    clinic_chat,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
PUBLIC_DIR = Path(__file__).resolve().parent / "public"

app = FastAPI(
    title="Chatbot v4",
    version="0.1.0",
    description=(
        "GET / (HTML), POST /chat (JSON), POST /ask_bot (urlencoded), POST /askbot (JSON or "
        "urlencoded, VE-25), GET /public/{path}, GET /health, /static."
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


def _safe_public_path(relative: str) -> Path | None:
    """Resolve *relative* under ``PUBLIC_DIR``; return the path only if it is a safe file."""
    if not relative.strip():
        return None
    base = PUBLIC_DIR.resolve()
    if not base.is_dir():
        return None
    candidate = (PUBLIC_DIR / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


@app.get(
    "/public/{resource_path:path}",
    summary="Public file",
)
async def serve_public(resource_path: str) -> FileResponse:
    """Serve files from ``public/`` with path traversal protection (VE-25)."""
    path = _safe_public_path(resource_path)
    if path is None:
        raise HTTPException(status_code=404, detail="Not found")
    media_type, _ = mimetypes.guess_type(str(path))
    return FileResponse(path, media_type=media_type or "application/octet-stream")


async def _parse_askbot_body(request: Request) -> tuple[str, str]:
    """Parse VE-25 ``/askbot`` body as JSON or urlencoded (no multipart)."""
    ct_raw = (request.headers.get("content-type") or "").lower()
    body = await request.body()
    if "application/json" in ct_raw:
        if not body.strip():
            raise HTTPException(status_code=422, detail="Empty JSON body")
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON body") from exc
        if not isinstance(data, dict):
            raise HTTPException(status_code=422, detail="JSON body must be an object")
        raw_msg = data.get("msg", "")
        raw_sid = data.get("session_id", "")
        return (
            "" if raw_msg is None else str(raw_msg),
            "" if raw_sid is None else str(raw_sid),
        )
    if "application/x-www-form-urlencoded" in ct_raw:
        fields = _parse_urlencoded_body(body)
        return fields.get("msg", ""), fields.get("session_id", "")
    raise HTTPException(
        status_code=415,
        detail=(
            "Content-Type must be application/json or "
            "application/x-www-form-urlencoded"
        ),
    )


async def _assistant_reply(user_text: str, session_id: str) -> AskBotResponse:
    """Call :data:`clinic_chat` with session config, record the turn, map LLM errors to HTTP."""
    config = {"configurable": {"session_id": session_id}}
    try:
        result = await clinic_chat.ainvoke(user_text, config)
    except LlmConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmUpstreamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    reply = result.content if isinstance(result.content, str) else str(result.content)
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
    """JSON chat: delegates to :data:`clinic_chat` and records memory."""
    return await _assistant_reply(body.msg, body.session_id)


@app.post(
    "/askbot",
    summary="Ask bot (VE-25)",
    response_model=AskBotResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["msg", "session_id"],
                        "properties": {
                            "msg": {"type": "string"},
                            "session_id": {"type": "string"},
                        },
                    }
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "msg": {"type": "string"},
                            "session_id": {"type": "string"},
                        },
                    }
                },
            }
        }
    },
)
async def askbot(request: Request) -> AskBotResponse:
    """JSON or urlencoded chat with strict ``msg`` / ``session_id`` validation (VE-25)."""
    msg_raw, session_raw = await _parse_askbot_body(request)
    msg = msg_raw.strip()
    session_id = session_raw.strip()
    if not msg or not session_id:
        raise HTTPException(
            status_code=422,
            detail="msg and session_id must be present and non-empty after trimming.",
        )
    return await _assistant_reply(msg, session_id)


def _parse_urlencoded_body(body_bytes: bytes) -> dict[str, str]:
    parsed = parse_qs(body_bytes.decode("utf-8"), keep_blank_values=True)
    flat: dict[str, str] = {}
    for key, values in parsed.items():
        if values:
            flat[key] = values[-1]
    return flat


def _validate_ask_bot_fields(msg: str | None, session_id: str | None) -> tuple[str, str]:
    if msg is None or session_id is None:
        raise HTTPException(
            status_code=422,
            detail="msg and session_id are required fields",
        )
    msg_clean = msg.strip()
    session_clean = session_id.strip()
    if not msg_clean or not session_clean:
        raise HTTPException(
            status_code=422,
            detail="msg and session_id must be non-empty strings",
        )
    return msg_clean, session_clean


@app.post(
    "/ask_bot",
    summary="Ask Bot",
    response_model=AskBotResponse,
)
async def ask_bot(request: Request) -> AskBotResponse:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" not in content_type:
        raise HTTPException(
            status_code=415,
            detail="Content-Type must be application/x-www-form-urlencoded",
        )
    body_bytes = await request.body()
    if not body_bytes.strip():
        raise HTTPException(status_code=422, detail="Request body is empty")
    fields = _parse_urlencoded_body(body_bytes)
    msg, session_id = _validate_ask_bot_fields(
        fields.get("msg"),
        fields.get("session_id"),
    )
    return await _assistant_reply(msg, session_id)


if STATIC_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )
