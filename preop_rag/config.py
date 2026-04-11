"""Versioned parameters for the pre-operative RAG pipeline (VE-22).

All values are committed so runs are traceable without reading inline comments
only. Bump ``PREOP_RAG_CONFIG_VERSION`` when any of these change.
"""

from __future__ import annotations

# Canonical config id (bump when chunking, URL, or default embedding model changes).
PREOP_RAG_CONFIG_VERSION = "preop-rag-2026-04-11"

# Official pre-operative instructions page (English) used as RAG source.
OFFICIAL_PREOP_DOC_URL = (
    "https://veterinary-clinic-teal.vercel.app/en/docs/instructions-before-operation"
)

# RecursiveCharacterTextSplitter (langchain_text_splitters).
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
SPLITTER_NAME = "RecursiveCharacterTextSplitter"

# Default embedding provider for production-style runs (OpenAI).
EMBEDDING_PROVIDER = "openai"
EMBEDDING_MODEL = "text-embedding-3-small"

# HTTP client: follow redirects (documented behavior for 301/302).
HTTP_TIMEOUT_SECONDS = 30.0
