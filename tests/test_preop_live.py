"""Optional live checks: network fetch against the official pre-op URL."""

from __future__ import annotations

import os

import pytest

from preop_rag.config import OFFICIAL_PREOP_DOC_URL
from preop_rag.fetch import fetch_preop_html
from preop_rag.runtime import (
    get_preop_vector_store,
    load_preop_rag_index,
    reset_preop_rag_runtime_for_tests,
)


@pytest.mark.preop_live
def test_fetch_official_preop_url() -> None:
    if os.environ.get("RUN_PREOP_RAG_LIVE") != "1":
        pytest.skip("Set RUN_PREOP_RAG_LIVE=1 to run live pre-op fetch tests")
    html = fetch_preop_html(OFFICIAL_PREOP_DOC_URL)
    assert len(html) > 200
    lowered = html.lower()
    assert "html" in lowered


@pytest.mark.preop_live
def test_full_index_build_fake_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.environ.get("RUN_PREOP_RAG_LIVE") != "1":
        pytest.skip("Set RUN_PREOP_RAG_LIVE=1 to run live pre-op fetch tests")
    monkeypatch.delenv("PREOP_RAG_LIVE_URL", raising=False)
    monkeypatch.setenv("PREOP_RAG_FAKE_EMBEDDINGS", "1")
    reset_preop_rag_runtime_for_tests()
    load_preop_rag_index()
    assert get_preop_vector_store() is not None
