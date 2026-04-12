"""Versioned parameters for the pre-operative RAG pipeline (VE-22).

All values are committed so runs are traceable without reading inline comments
only. Bump ``PREOP_RAG_CONFIG_VERSION`` when any of these change.
"""

from __future__ import annotations

# Canonical config id (bump when chunking, URL, or default embedding model changes).
PREOP_RAG_CONFIG_VERSION = "preop-rag-ve28-2026-04-12"

# Official pre-operative instructions page (English) used as RAG source.
# VET-11 evidence: README § Pre-op RAG (URL + tests + runtime log).
OFFICIAL_PREOP_DOC_URL = (
    "https://veterinary-clinic-teal.vercel.app/en/docs/instructions-before-operation"
)

# RecursiveCharacterTextSplitter (langchain_text_splitters); sizes are in characters.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SPLITTER_NAME = "RecursiveCharacterTextSplitter"

# Retrieved chunks appended to the system prompt per chat turn.
TOP_K_RESULTS = 3

# Default embedding provider for production-style runs (OpenAI).
EMBEDDING_PROVIDER = "openai"
EMBEDDING_MODEL = "text-embedding-3-small"

# HTTP client: follow redirects (documented behavior for 301/302).
HTTP_TIMEOUT_SECONDS = 30.0
