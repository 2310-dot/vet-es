"""In-process, session-scoped chat memory (VE-21).

Stores recent user/assistant message pairs per trimmed ``session_id`` (keys are
case-sensitive). Thread-safe with a single process-wide lock: concurrent
updates for the same session serialize; the last writer under the lock wins.

Environment:

* ``CHAT_MEMORY_MAX_TURNS`` — max completed user→assistant pairs kept per
  session (default ``50``). Oldest pairs are dropped when over the limit.
* ``CHAT_MEMORY_TTL_SECONDS`` — if ``0`` (default), TTL is disabled and entries
  live until process exit. If positive, a session whose last touch is older
  than this many seconds (see :func:`time.monotonic`) is treated as empty on
  the next access.

Restarting the process clears all data. There is no persistence.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Literal

Role = Literal["user", "assistant"]
Message = tuple[Role, str]

_lock = threading.Lock()
# session_id -> (ordered messages, last_touch_monotonic)
_sessions: dict[str, tuple[list[Message], float]] = {}


def _read_max_turns() -> int:
    """Maximum pairs to retain per session (at least 1)."""
    raw = os.environ.get("CHAT_MEMORY_MAX_TURNS", "50")
    try:
        n = int(str(raw).strip())
    except ValueError:
        return 50
    return max(1, n)


def _read_ttl_seconds() -> float:
    """TTL in seconds; ``0`` means disabled (no expiry while process runs)."""
    raw = os.environ.get("CHAT_MEMORY_TTL_SECONDS", "0")
    try:
        sec = float(str(raw).strip())
    except ValueError:
        return 0.0
    return max(0.0, sec)


def _trim_oldest_pairs(messages: list[Message], max_pairs: int) -> None:
    """Drop oldest user/assistant pairs in place."""
    cap = max_pairs * 2
    while len(messages) > cap:
        messages.pop(0)
        messages.pop(0)


def record_exchange(session_id: str, user: str, assistant: str) -> int:
    """Append one user message and one assistant reply for *session_id*.

    *session_id* must already be trimmed; keys are compared case-sensitively.

    :param session_id: Trimmed session identifier.
    :param user: User message text (validated/cleaned by the caller).
    :param assistant: Assistant reply text for this turn.
    :return: Number of completed user→assistant pairs stored for this session
        after this write (always >= 1).
    """
    max_pairs = _read_max_turns()
    ttl = _read_ttl_seconds()
    now = time.monotonic()
    with _lock:
        if session_id not in _sessions:
            messages = []
        else:
            messages, last_touch = _sessions[session_id]
            if ttl > 0.0 and (now - last_touch) > ttl:
                messages = []
        messages.append(("user", user))
        messages.append(("assistant", assistant))
        _trim_oldest_pairs(messages, max_pairs)
        _sessions[session_id] = (messages, now)
        return len(messages) // 2


def session_messages_copy(session_id: str) -> list[Message]:
    """Return a copy of stored messages for *session_id*, or an empty list.

    Applies the same TTL rule as :func:`record_exchange` for reads (expired
    sessions appear empty). Does not update last-touch time.

    :param session_id: Trimmed session identifier.
    :return: Shallow copy of ``(role, text)`` tuples in order.
    """
    ttl = _read_ttl_seconds()
    now = time.monotonic()
    with _lock:
        if session_id not in _sessions:
            return []
        messages, last_touch = _sessions[session_id]
        if ttl > 0.0 and (now - last_touch) > ttl:
            return []
        return list(messages)


def reset_chat_memory_for_tests() -> None:
    """Remove all sessions. Intended for test isolation only."""
    with _lock:
        _sessions.clear()
