"""Canonical pre-op RAG configuration (VET-11: traceable official source URL)."""

from __future__ import annotations

from preop_rag.config import OFFICIAL_PREOP_DOC_URL


def test_official_preop_doc_url_is_case_study_instructions_page() -> None:
    """Index ingest uses this exact URL unless PREOP_RAG_LIVE_URL overrides (see runtime)."""
    assert OFFICIAL_PREOP_DOC_URL == (
        "https://veterinary-clinic-teal.vercel.app/en/docs/instructions-before-operation"
    )
    assert OFFICIAL_PREOP_DOC_URL.startswith("https://")
