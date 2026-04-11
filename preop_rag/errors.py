"""Errors for the pre-op RAG pipeline."""


class PreopSourceFetchError(RuntimeError):
    """Raised when the pre-op source URL cannot be fetched successfully."""

    pass


class PreopIngestError(RuntimeError):
    """Raised when fetched content cannot be normalized into non-empty text."""

    pass
