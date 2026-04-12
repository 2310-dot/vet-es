"""Shared pytest hooks (VE-28: isolate pre-op RAG module state)."""

from __future__ import annotations

import pytest

from preop_rag.runtime import reset_preop_rag_runtime_for_tests


@pytest.fixture(autouse=True)
def _reset_preop_rag_state() -> None:
    reset_preop_rag_runtime_for_tests()
    yield
    reset_preop_rag_runtime_for_tests()
