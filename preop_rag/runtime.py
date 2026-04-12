"""Load and hold the pre-op RAG index for the FastAPI app (VE-28).

Fetches :data:`~preop_rag.config.OFFICIAL_PREOP_DOC_URL` at startup (or
``PREOP_RAG_LIVE_URL`` when set), builds an in-memory vector store, and exposes
read-only accessors for :mod:`llm_service`.
"""

from __future__ import annotations

import logging
import os
from threading import Lock

from langchain_core.vectorstores import InMemoryVectorStore

from preop_rag.config import OFFICIAL_PREOP_DOC_URL, TOP_K_RESULTS
from preop_rag.embeddings_factory import get_preop_embeddings
from preop_rag.errors import PreopIngestError, PreopSourceFetchError
from preop_rag.extract import html_to_documents
from preop_rag.fetch import fetch_preop_html
from preop_rag.pipeline import build_vector_store, split_documents

logger = logging.getLogger(__name__)

_lock = Lock()
_vector_store: InMemoryVectorStore | None = None
_fetch_failed: bool = False
_indexed_source_url: str | None = None

# Exact user-facing copy when the official page cannot be fetched (VE-28).
PREOP_SOURCE_UNAVAILABLE_USER_MESSAGE = (
    "No se pudo acceder a la fuente de información preoperatoria. "
    "Por favor, inténtalo de nuevo."
)


def looks_like_preoperative_question(text: str) -> bool:
    """Heuristic: Spanish pre-op / fasting / surgery prep queries (VE-28)."""
    t = text.lower()
    needles = (
        "ayuno",
        "ayunar",
        "ayunas",
        "operación",
        "operacion",
        "cirugía",
        "cirugia",
        "preoperatorio",
        "preoperatoria",
        "preparación",
        "preparacion",
        "antes de la operación",
        "antes de la operacion",
        "agua",
        "comida",
        "ingesta",
        "hospitalización",
        "hospitalizacion",
        "sedación",
        "sedacion",
        "anestesia",
    )
    return any(n in t for n in needles)


def reset_preop_rag_runtime_for_tests() -> None:
    """Clear module state (pytest only)."""
    global _vector_store, _fetch_failed, _indexed_source_url
    with _lock:
        _vector_store = None
        _fetch_failed = False
        _indexed_source_url = None


def preop_source_fetch_failed() -> bool:
    """True when the last load attempt could not fetch or parse the HTML."""
    with _lock:
        return _fetch_failed


def get_preop_vector_store() -> InMemoryVectorStore | None:
    """Return the in-memory store when indexing succeeded."""
    with _lock:
        return _vector_store


def get_preop_top_k() -> int:
    """Configured retrieval depth (for tests and callers)."""
    return TOP_K_RESULTS


def get_indexed_preop_source_url() -> str | None:
    """URL string used for the current index, if any."""
    with _lock:
        return _indexed_source_url


def _resolve_source_url() -> str:
    override = os.environ.get("PREOP_RAG_LIVE_URL", "").strip()
    return override or OFFICIAL_PREOP_DOC_URL


def _fake_embeddings_enabled() -> bool:
    return os.environ.get("PREOP_RAG_FAKE_EMBEDDINGS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def load_preop_rag_index() -> None:
    """Fetch, parse, chunk, and embed the official pre-op page (sync).

    Safe to call from a thread pool. On failure, logs and sets flags so the
    API can degrade without crashing.
    """
    global _vector_store, _fetch_failed, _indexed_source_url
    url = _resolve_source_url()

    with _lock:
        _fetch_failed = False
        _vector_store = None
        _indexed_source_url = None

    try:
        html = fetch_preop_html(url)
    except PreopSourceFetchError:
        logger.exception("Pre-op RAG: failed to fetch source URL %s", url)
        with _lock:
            _fetch_failed = True
        return

    try:
        docs = html_to_documents(html, source_url=url)
        chunks = split_documents(docs)
    except PreopIngestError:
        logger.exception("Pre-op RAG: failed to extract text from %s", url)
        with _lock:
            _fetch_failed = True
        return

    fake = _fake_embeddings_enabled()
    has_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    if not fake and not has_key:
        logger.warning(
            "Pre-op RAG disabled: set OPENAI_API_KEY or PREOP_RAG_FAKE_EMBEDDINGS=1"
        )
        return

    try:
        embeddings = get_preop_embeddings(prefer_openai=not fake)
        store = build_vector_store(chunks, embeddings)
    except Exception:
        logger.exception("Pre-op RAG: embedding or vector store build failed")
        return

    with _lock:
        _vector_store = store
        _indexed_source_url = url
    logger.info(
        "Pre-op RAG index ready (source=%s, chunks=%s, fake_embeddings=%s)",
        url,
        len(chunks),
        fake,
    )
