"""Tests for pre-operative RAG pipeline (VE-22)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from langchain_core.embeddings import Embeddings

from preop_rag.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OFFICIAL_PREOP_DOC_URL,
    PREOP_RAG_CONFIG_VERSION,
    SPLITTER_NAME,
)
from preop_rag.embeddings_factory import get_preop_embeddings
from preop_rag.errors import PreopIngestError, PreopSourceFetchError
from preop_rag.extract import html_to_documents
from preop_rag.fetch import fetch_preop_html
from preop_rag.pipeline import (
    build_vector_store,
    retrieve_top_k,
    split_documents,
)

FIXTURE_HTML = Path(__file__).resolve().parent / "fixtures" / "sample_preop_page.html"
BENCHMARK_QUERY = "fasting hours before surgery water admission"
BENCHMARK_MARKER = "VE22_BENCHMARK_FASTING"


class _ZeroEmbeddings(Embeddings):
    """All-zero vectors so similarity scores tie; stable single-chunk retrieval."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:  # noqa: ARG002
        return [[0.0] * 16 for _ in texts]

    def embed_query(self, text: str) -> list[float]:  # noqa: ARG002
        return [0.0] * 16


def test_config_constants_are_documented() -> None:
    assert PREOP_RAG_CONFIG_VERSION
    assert OFFICIAL_PREOP_DOC_URL.startswith("https://")
    assert CHUNK_SIZE >= 1
    assert CHUNK_OVERLAP >= 0
    assert CHUNK_OVERLAP < CHUNK_SIZE
    assert SPLITTER_NAME
    assert EMBEDDING_PROVIDER == "openai"
    assert EMBEDDING_MODEL


def test_fetch_http_error_raises_preop_source_fetch_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found", request=request)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with pytest.raises(PreopSourceFetchError) as exc_info:
            fetch_preop_html("https://example.invalid/preop", client=client)
    assert "fetch failed" in str(exc_info.value).lower()
    assert "404" in str(exc_info.value)


def test_html_to_documents_empty_body_raises() -> None:
    with pytest.raises(PreopIngestError):
        html_to_documents("<html><body></body></html>", source_url="https://x.test")


def test_end_to_end_fixture_chunk_embed_retrieve_grounding() -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8")
    url = "https://fixture.local/preop"
    docs = html_to_documents(html, source_url=url)
    normalized = docs[0].page_content
    assert BENCHMARK_MARKER in normalized

    chunks = split_documents(docs)
    assert len(chunks) >= 1
    for ch in chunks:
        assert ch.metadata.get("source") == url
        assert ch.metadata.get("splitter") == SPLITTER_NAME
        assert ch.page_content in normalized

    store = build_vector_store(chunks, _ZeroEmbeddings())
    hits_3 = retrieve_top_k(store, BENCHMARK_QUERY, k=3)
    assert len(hits_3) <= 3
    hits_1 = retrieve_top_k(store, BENCHMARK_QUERY, k=1)
    assert len(hits_1) == 1

    corpus = normalized
    for hit in hits_3:
        assert hit.page_content in corpus

    assert BENCHMARK_MARKER in hits_1[0].page_content


def test_retrieve_top_k_rejects_non_positive() -> None:
    html = FIXTURE_HTML.read_text(encoding="utf-8")
    docs = html_to_documents(html, source_url="https://fixture.local/preop")
    chunks = split_documents(docs)
    store = build_vector_store(chunks, _ZeroEmbeddings())
    with pytest.raises(ValueError, match="top_k"):
        retrieve_top_k(store, "x", k=0)


def test_get_preop_embeddings_openai_without_key_raises() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_preop_embeddings(prefer_openai=True)


def test_get_preop_embeddings_fake_when_no_key() -> None:
    emb = get_preop_embeddings(prefer_openai=False)
    vec = emb.embed_query("hello")
    assert len(vec) == 1536


@pytest.mark.preop_live
def test_live_url_fetch_and_openai_embeddings() -> None:
    """Optional: set RUN_PREOP_RAG_LIVE=1 and OPENAI_API_KEY; hits real network."""
    import os

    if os.environ.get("RUN_PREOP_RAG_LIVE", "").strip() != "1":
        pytest.skip("Set RUN_PREOP_RAG_LIVE=1 to run live pre-op RAG test.")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        pytest.skip("OPENAI_API_KEY required for live embedding test.")

    html = fetch_preop_html(OFFICIAL_PREOP_DOC_URL)
    docs = html_to_documents(html, source_url=OFFICIAL_PREOP_DOC_URL)
    chunks = split_documents(docs)
    store = build_vector_store(chunks, get_preop_embeddings(prefer_openai=True))
    hits = retrieve_top_k(store, BENCHMARK_QUERY, k=3)
    assert len(hits) >= 1
    corpus = docs[0].page_content
    assert any(h.page_content in corpus for h in hits)
