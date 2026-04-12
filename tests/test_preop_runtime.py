"""Tests for pre-op RAG runtime bootstrap (VE-28)."""

from __future__ import annotations

from pathlib import Path

import pytest

from preop_rag.errors import PreopSourceFetchError
from preop_rag.config import OFFICIAL_PREOP_DOC_URL
from preop_rag.runtime import (
    get_indexed_preop_source_url,
    get_preop_vector_store,
    load_preop_rag_index,
    preop_source_fetch_failed,
    reset_preop_rag_runtime_for_tests,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_preop_page.html"


def test_load_index_with_fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr(
        "preop_rag.runtime.fetch_preop_html",
        lambda url: html,
    )
    monkeypatch.setenv("PREOP_RAG_FAKE_EMBEDDINGS", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PREOP_RAG_LIVE_URL", raising=False)
    reset_preop_rag_runtime_for_tests()
    load_preop_rag_index()
    assert preop_source_fetch_failed() is False
    assert get_preop_vector_store() is not None
    assert get_indexed_preop_source_url() == OFFICIAL_PREOP_DOC_URL


def test_load_index_sets_fetch_failed_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_url: str) -> str:
        raise PreopSourceFetchError("simulated failure")

    monkeypatch.setattr("preop_rag.runtime.fetch_preop_html", boom)
    reset_preop_rag_runtime_for_tests()
    load_preop_rag_index()
    assert preop_source_fetch_failed() is True
    assert get_preop_vector_store() is None


def test_load_index_skips_without_key_or_fake_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    monkeypatch.setattr("preop_rag.runtime.fetch_preop_html", lambda _u: html)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PREOP_RAG_FAKE_EMBEDDINGS", raising=False)
    reset_preop_rag_runtime_for_tests()
    load_preop_rag_index()
    assert preop_source_fetch_failed() is False
    assert get_preop_vector_store() is None
