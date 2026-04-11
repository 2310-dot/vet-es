"""Chunk, embed, and retrieve pre-operative documentation (VE-22)."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from preop_rag.config import CHUNK_OVERLAP, CHUNK_SIZE, SPLITTER_NAME


def split_documents(documents: list[Document]) -> list[Document]:
    """Split documents with configured chunk size and overlap.

    :param documents: Input documents (typically one full-page document).
    :return: Chunked documents with inherited metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)
    for i, chunk in enumerate(chunks):
        chunk.metadata = {
            **chunk.metadata,
            "chunk_index": i,
            "splitter": SPLITTER_NAME,
        }
    return chunks


def build_vector_store(
    documents: list[Document],
    embeddings: Embeddings,
) -> InMemoryVectorStore:
    """Embed documents and return an in-memory vector store.

    :param documents: Chunked documents.
    :param embeddings: Embedding model.
    :return: Populated ``InMemoryVectorStore``.
    """
    return InMemoryVectorStore.from_documents(
        documents=documents,
        embedding=embeddings,
    )


def retrieve_top_k(
    store: InMemoryVectorStore,
    query: str,
    k: int,
) -> list[Document]:
    """Similarity search with explicit top-``k`` validation.

    :param store: Vector store built from pre-op chunks.
    :param query: Natural language query.
    :param k: Number of documents to return (must be >= 1).
    :return: Up to ``k`` documents.
    :raises ValueError: If ``k`` is not a positive integer.
    """
    if k < 1:
        raise ValueError(f"top_k must be >= 1, got {k}")
    return store.similarity_search(query, k=k)
