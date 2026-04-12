"""Tests for pre-op HTML text extraction (VE-28)."""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from preop_rag.extract import html_to_documents

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_preop_page.html"


def test_html_to_documents_strips_nav_footer_noise() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    docs = html_to_documents(html, source_url="https://example.invalid/preop")
    assert len(docs) == 1
    body = docs[0].page_content
    assert "VE22_BENCHMARK_FASTING" in body
    assert "Instructions before operation" in body
    assert "Home" not in body


def test_html_to_documents_metadata_source() -> None:
    doc = html_to_documents("<html><body><p>Only</p></body></html>", source_url="https://x/y")[0]
    assert isinstance(doc, Document)
    assert doc.metadata.get("source") == "https://x/y"
