"""Pre-operative documentation RAG pipeline (VE-22).

Ingests the official pre-op URL, chunks with documented parameters, embeds,
and retrieves via LangChain ``InMemoryVectorStore``.
"""

from preop_rag.config import PREOP_RAG_CONFIG_VERSION

__all__ = ["PREOP_RAG_CONFIG_VERSION"]
