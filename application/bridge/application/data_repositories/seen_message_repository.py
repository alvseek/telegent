"""Storage for message ids already answered, so a redelivery is not answered twice.

The bridge was stateless by design and this is the one exception, forced by the
transport rather than chosen: Meta retries a webhook whose 200 it did not see in
time, and the retry carries the same ``wamid``. Telegram needed nothing like this
because its library confirms an update batch before the handlers run — which is
why the earlier decision to skip a dedupe store was right then and does not
transfer now.

**The check and the write are one statement.** ``INSERT OR IGNORE`` followed by
reading ``rowcount`` cannot interleave the way "does it exist? then insert" can,
so two concurrent deliveries of the same id can never both be told they are new.
That is the whole reason this is not a Python set with a lock around it.

A connection is opened per call rather than held. At this volume — a handful of
messages a minute — the cost is irrelevant, and it removes SQLite's thread
affinity from a process where the caller may be a request handler on the event
loop or a background task on a worker thread.
"""
from __future__ import annotations

import sqlite3
import time

from application.data_entities.seen_message import SeenMessage

DEFAULT_RETENTION_SECONDS = 48 * 60 * 60  # far beyond any retry window; slack, not a requirement

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_message (
    wamid   TEXT PRIMARY KEY,
    seen_at INTEGER NOT NULL
)
"""


class SeenMessageRepository:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        with self._connect() as conn:
            # WAL lets a reader and a writer coexist, which matters once the ack
            # path and a background task touch this file at the same moment.
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5.0)

    def mark_seen(self, wamid: str, now: int | None = None) -> bool:
        """Record ``wamid`` and say whether it was new.

        Returns True the first time an id is presented and False for every
        redelivery. Callers treat False as "already answered, do nothing" — so a
        caller that inverts this is one that answers everything twice.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO seen_message (wamid, seen_at) VALUES (?, ?)",
                (wamid, int(time.time()) if now is None else now),
            )
            return cursor.rowcount == 1

    def purge_older_than(
        self, retention_seconds: int = DEFAULT_RETENTION_SECONDS, now: int | None = None
    ) -> int:
        """Drop rows past the retention window. Returns how many were removed."""
        cutoff = (int(time.time()) if now is None else now) - retention_seconds
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM seen_message WHERE seen_at < ?", (cutoff,)
            )
            return cursor.rowcount

    def get(self, wamid: str) -> SeenMessage | None:
        """Read one row back. Used by tests and by anyone debugging a redelivery."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT wamid, seen_at FROM seen_message WHERE wamid = ?", (wamid,)
            ).fetchone()
        return None if row is None else SeenMessage(wamid=row[0], seen_at=row[1])
