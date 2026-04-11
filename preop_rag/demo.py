"""Runnable demo: fetch, index, and query the official pre-op page (VE-22).

Usage::

    python -m preop_rag.demo

Requires ``OPENAI_API_KEY`` for real embeddings. Without it, pass
``--fake-embeddings`` to use deterministic fake vectors (local sanity check
only).

Environment:

- ``PREOP_RAG_LIVE_URL``: optional override for the source URL.
"""

from __future__ import annotations

import argparse
import os
import sys

from preop_rag.config import (
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    OFFICIAL_PREOP_DOC_URL,
    PREOP_RAG_CONFIG_VERSION,
)
from preop_rag.embeddings_factory import get_preop_embeddings
from preop_rag.extract import html_to_documents
from preop_rag.fetch import fetch_preop_html
from preop_rag.pipeline import build_vector_store, retrieve_top_k, split_documents


def _log_run_banner(url: str, *, use_fake: bool) -> None:
    print(
        f"preop_rag config_version={PREOP_RAG_CONFIG_VERSION} "
        f"embedding_provider={EMBEDDING_PROVIDER} "
        f"embedding_model={EMBEDDING_MODEL} "
        f"fake_embeddings={use_fake}",
        file=sys.stderr,
    )
    print(f"source_url={url}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pre-op RAG demo (VE-22).")
    parser.add_argument(
        "--url",
        default=os.environ.get("PREOP_RAG_LIVE_URL", OFFICIAL_PREOP_DOC_URL),
        help="Source URL (default: official pre-op page or PREOP_RAG_LIVE_URL).",
    )
    parser.add_argument(
        "--query",
        default="fasting instructions before surgery water food",
        help="Benchmark retrieval query.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        dest="top_k",
        help="Retriever top-k.",
    )
    parser.add_argument(
        "--fake-embeddings",
        action="store_true",
        help="Use FakeEmbeddings instead of OpenAI (no API key).",
    )
    args = parser.parse_args(argv)

    use_fake = args.fake_embeddings
    _log_run_banner(args.url, use_fake=use_fake)

    html = fetch_preop_html(args.url)
    docs = html_to_documents(html, source_url=args.url)
    chunks = split_documents(docs)
    embeddings = get_preop_embeddings(prefer_openai=not use_fake)
    store = build_vector_store(chunks, embeddings)
    hits = retrieve_top_k(store, args.query, k=args.top_k)

    print(f"query={args.query!r} top_k={args.top_k} hits={len(hits)}", file=sys.stderr)
    for i, doc in enumerate(hits):
        src = doc.metadata.get("source", "")
        idx = doc.metadata.get("chunk_index", "")
        preview = doc.page_content[:200].replace("\n", " ")
        print(f"--- hit {i + 1} source={src} chunk_index={idx}")
        print(doc.page_content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
