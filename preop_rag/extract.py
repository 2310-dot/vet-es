"""Extract plain text from HTML for chunking (VE-22)."""

from __future__ import annotations

from bs4 import BeautifulSoup
from langchain_core.documents import Document

from preop_rag.errors import PreopIngestError


def html_to_documents(html: str, *, source_url: str) -> list[Document]:
    """Strip tags and return a single :class:`~langchain_core.documents.Document`.

    :param html: Raw HTML.
    :param source_url: Canonical source URL stored in metadata.
    :return: One-document list for downstream splitting.
    :raises PreopIngestError: If no textual content remains after extraction.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [ln.strip() for ln in text.splitlines()]
    collapsed = "\n".join(ln for ln in lines if ln)
    cleaned = collapsed.strip()
    if not cleaned:
        raise PreopIngestError(
            f"Pre-op HTML produced empty text after extraction for source {source_url!r}"
        )
    return [
        Document(
            page_content=cleaned,
            metadata={"source": source_url},
        )
    ]
