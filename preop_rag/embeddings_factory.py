"""Select embedding implementation (OpenAI vs deterministic fake for tests)."""

from __future__ import annotations

import os

from langchain_community.embeddings import FakeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from preop_rag.config import EMBEDDING_MODEL


def get_preop_embeddings(*, prefer_openai: bool | None = None) -> Embeddings:
    """Return embeddings for indexing and query.

    If ``prefer_openai`` is True, or ``OPENAI_API_KEY`` is set and
    ``prefer_openai`` is not False, use :class:`OpenAIEmbeddings`.

    Otherwise use :class:`FakeEmbeddings` (deterministic; for CI and offline
    tests). Dimension matches OpenAI ``text-embedding-3-small`` (1536) so the
    same vector store shape is used.

    :param prefer_openai: Override auto-detection when set.
    :return: LangChain ``Embeddings`` instance.
    :raises ValueError: If ``prefer_openai`` is True but the API key is missing.
    """
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    use_openai = prefer_openai if prefer_openai is not None else bool(key)
    if use_openai and not key:
        raise ValueError(
            "OPENAI_API_KEY is required when using OpenAI embeddings "
            "(set prefer_openai=False for FakeEmbeddings)."
        )
    if use_openai:
        return OpenAIEmbeddings(model=EMBEDDING_MODEL)
    return FakeEmbeddings(size=1536)
