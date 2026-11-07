"""Append-only SQLite event log (ground retention, FR-03/FR-14). Idempotent by event_id."""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Optional


class EventStore:
    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.Lock()
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS events (
                 gseq INTEGER PRIMARY KEY AUTOINCREMENT,
                 event_id TEXT UNIQUE NOT NULL,
                 incident_id TEXT,
                 type TEXT NOT NULL,
                 node_id TEXT,
                 capture_ts REAL NOT NULL,
                 recorded_ts REAL NOT NULL,
                 payload TEXT NOT NULL)"""
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS ev_inc ON events(incident_id, capture_ts)")

    def append(self, event: dict[str, Any]) -> bool:
        """Insert an event. Returns False (and changes nothing) if event_id was already stored."""
        with self._lock:
            cur = self._db.execute(
                "INSERT OR IGNORE INTO events(event_id, incident_id, type, node_id, capture_ts,"
                " recorded_ts, payload) VALUES (?,?,?,?,?,?,?)",
                (
                    event["event_id"], event.get("incident_id"), event["type"], event.get("node_id"),
                    float(event["capture_ts"]), float(event.get("recorded_ts", event["capture_ts"])),
                    json.dumps(event, default=str),
                ),
            )
            return cur.rowcount == 1

    def history(self, incident_id: Optional[str] = None, limit: int = 2000) -> list[dict]:
        """Events in capture-time order (ties broken by arrival)."""
        q = "SELECT payload FROM events"
        args: tuple = ()
        if incident_id is not None:
            q += " WHERE incident_id = ?"
            args = (incident_id,)
        q += " ORDER BY capture_ts, gseq LIMIT ?"
        with self._lock:
            rows = self._db.execute(q, args + (limit,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def count(self, incident_id: Optional[str] = None) -> int:
        with self._lock:
            if incident_id is None:
                return self._db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            return self._db.execute(
                "SELECT COUNT(*) FROM events WHERE incident_id = ?", (incident_id,)
            ).fetchone()[0]
