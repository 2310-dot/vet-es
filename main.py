"""Chatbot v4 placeholder API: GET / (HTML chat demo), GET /health, POST /chat (JSON)."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Chatbot v4",
    version="0.1.0",
    description=(
        "Placeholder API for clinic chatbot: HTML chat demo on /, JSON /chat, "
        "form-based /ask_bot, and /health liveness."
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
    """Stub response for POST /ask_bot until LangChain is added."""

    msg: str = Field(examples=["hello"])
    session_id: str = Field(examples=["s1"])
    placeholder: bool = True


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


@app.post(
    "/chat",
    summary="Chat",
    response_model=AskBotResponse,
)
async def chat(body: ChatRequest) -> AskBotResponse:
    """JSON chat placeholder: echoes validated message until LangChain is wired."""
    return AskBotResponse(
        msg=body.msg,
        session_id=body.session_id,
        placeholder=True,
    )


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
    return AskBotResponse(msg=msg, session_id=session_id, placeholder=True)


if STATIC_DIR.is_dir():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static",
    )
