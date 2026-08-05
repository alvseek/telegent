"""Per-chat conversation memory: SQLite-persisted, bounded window.

Each Telegram chat is isolated by ``chat_id`` (this is what makes the bot
multi-user-ready for free). History survives restarts because it lives in a
SQLite file, and ``get_history`` returns only the most recent ``limit`` turns
so the token cost per reply stays bounded.
"""
from __future__ import annotations

import sqlite3
import time
from typing import List, Tuple

# (role, content) — role is "user" or "assistant"
Turn = Tuple[str, str]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id  INTEGER NOT NULL,
    role     TEXT    NOT NULL,
    content  TEXT    NOT NULL,
    ts       REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id);
"""


class MemoryStore:
    """A tiny SQLite-backed conversation store."""

    def __init__(self, db_path: str) -> None:
        # check_same_thread=False: python-telegram-bot runs handlers on an
        # event loop; a single long-lived connection is safe for one process.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, chat_id: int, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO messages (chat_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, time.time()),
        )
        self._conn.commit()

    def get_history(self, chat_id: int, limit: int) -> List[Turn]:
        """Return the last ``limit`` turns for a chat, oldest-first."""
        rows = self._conn.execute(
            "SELECT role, content FROM messages WHERE chat_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [(role, content) for role, content in reversed(rows)]

    def close(self) -> None:
        self._conn.close()
