"""
session_memory.py — thread-safe in-memory conversation history store.

Each session is keyed by a UUID session_id.  History is a list of
{"role": "user"|"assistant", "content": "..."} dicts.

For AWS deployment: replace this class with a DynamoDB or Redis-backed store.
The interface (get_history, add_turn, clear_session) stays the same.
"""

import time
from threading import Lock
from typing import Any, Dict, List, Optional

from app.utils.logger import setup_logger

log = setup_logger("session_memory")

# Maximum conversation turns kept per session (older turns are dropped)
_DEFAULT_MAX_TURNS = 20
# Sessions idle for longer than this are eligible for cleanup (seconds)
_DEFAULT_TTL = 3600  # 1 hour


class SessionMemory:
    """Thread-safe in-memory store for multi-turn conversation history."""

    def __init__(
        self,
        max_turns: int = _DEFAULT_MAX_TURNS,
        ttl_seconds: int = _DEFAULT_TTL,
    ) -> None:
        # { session_id: {"history": [...], "created_at": float, "last_active": float} }
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds

    # ── Public API ────────────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return the conversation history for a session (newest last)."""
        with self._lock:
            return list(self._store.get(session_id, {}).get("history", []))

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append a user + assistant turn to the session history."""
        with self._lock:
            now = time.time()
            if session_id not in self._store:
                self._store[session_id] = {
                    "history": [],
                    "created_at": now,
                    "last_active": now,
                }

            session = self._store[session_id]
            session["history"].append({"role": "user", "content": user_msg})
            session["history"].append({"role": "assistant", "content": assistant_msg})
            session["last_active"] = now

            # Trim to max_turns (each turn = 1 user + 1 assistant message)
            max_msgs = self.max_turns * 2
            if len(session["history"]) > max_msgs:
                session["history"] = session["history"][-max_msgs:]

    def get_info(self, session_id: str) -> Dict[str, Any]:
        """Return metadata about a session."""
        with self._lock:
            session = self._store.get(session_id, {})
            return {
                "session_id": session_id,
                "turn_count": len(session.get("history", [])) // 2,
                "created_at": session.get("created_at"),
                "last_active": session.get("last_active"),
                "exists": bool(session),
            }

    def clear_session(self, session_id: str) -> None:
        """Delete a session and its history."""
        with self._lock:
            removed = self._store.pop(session_id, None)
            if removed is not None:
                log.info(f"Cleared session: {session_id}")

    def active_session_count(self) -> int:
        """Return the number of currently tracked sessions."""
        with self._lock:
            return len(self._store)

    def evict_expired(self) -> int:
        """Remove sessions that have been idle longer than ttl_seconds."""
        now = time.time()
        with self._lock:
            expired = [
                sid
                for sid, data in self._store.items()
                if (now - data.get("last_active", 0)) > self.ttl_seconds
            ]
            for sid in expired:
                del self._store[sid]
        if expired:
            log.info(f"Evicted {len(expired)} expired sessions")
        return len(expired)


# ── Module-level singleton ────────────────────────────────────────────────────
# Imported by FastAPI main.py; shared across all requests within the process.
session_memory = SessionMemory()
