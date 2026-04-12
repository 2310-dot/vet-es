"""End-to-end pre-op RAG pipeline with fixture HTML (VE-28)."""

from __future__ import annotations

from pathlib import Path

from langchain_community.embeddings import FakeEmbeddings
from langchain_core.documents import Document

from preop_rag.extract import html_to_documents
from preop_rag.pipeline import build_vector_store, retrieve_top_k, split_documents

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_preop_page.html"


def test_pipeline_retrieves_fasting_benchmark_chunk() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    docs = html_to_documents(html, source_url="fixture://sample_preop_page.html")
    chunks = split_documents(docs)
    store = build_vector_store(chunks, FakeEmbeddings(size=1536))
    hits = retrieve_top_k(store, "How long must the patient fast before surgery?", k=3)
    joined = "\n".join(h.page_content for h in hits)
    assert "VE22_BENCHMARK_FASTING" in joined
    assert "twelve hours" in joined.lower()


def test_retrieve_top_k_rejects_zero() -> None:
    store = build_vector_store(
        [Document(page_content="a", metadata={})],
        FakeEmbeddings(size=1536),
    )
    try:
        retrieve_top_k(store, "q", k=0)
    except ValueError as exc:
        assert "top_k" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")
