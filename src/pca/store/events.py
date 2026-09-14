"""Append-only event log. This log IS the task state (spec §29, §30)."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from pca.core.provenance import Trust

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id   TEXT    NOT NULL,
    seq       INTEGER NOT NULL,
    ts        TEXT    NOT NULL,
    kind      TEXT    NOT NULL,
    payload   TEXT    NOT NULL,
    trust     INTEGER NOT NULL,
    UNIQUE (task_id, seq)
);
CREATE INDEX IF NOT EXISTS events_task ON events (task_id, seq);

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events table is append-only');
END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events table is append-only');
END;
"""


class EventKind(StrEnum):
    TASK_STARTED = "task_started"
    OBSERVED = "observed"
    PLANNED = "planned"
    POLICY_CHECKED = "policy_checked"
    RISK_CLASSIFIED = "risk_classified"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    ACTION_EXECUTED = "action_executed"
    VERIFIED = "verified"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    TASK_FINISHED = "task_finished"
    ERROR = "error"


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    seq: int
    task_id: str
    ts: str
    kind: EventKind
    payload: dict[str, Any]
    trust: Trust


class EventStore:
    """The only writer of task state. Offers no update and no delete."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.executescript(_SCHEMA)

    def append(
        self,
        task_id: str,
        kind: EventKind,
        payload: dict[str, Any],
        trust: Trust = Trust.SYSTEM_POLICY,
    ) -> Event:
        ts = datetime.now(UTC).isoformat()
        cursor = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM events WHERE task_id = ?",
            (task_id,),
        )
        seq = int(cursor.fetchone()[0])
        self._conn.execute(
            "INSERT INTO events (task_id, seq, ts, kind, payload, trust) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, seq, ts, kind.value, json.dumps(payload), int(trust)),
        )
        return Event(seq=seq, task_id=task_id, ts=ts, kind=kind, payload=payload, trust=trust)

    def events(self, task_id: str) -> list[Event]:
        rows = self._conn.execute(
            "SELECT seq, task_id, ts, kind, payload, trust FROM events"
            " WHERE task_id = ? ORDER BY seq",
            (task_id,),
        ).fetchall()
        return [
            Event(
                seq=row[0],
                task_id=row[1],
                ts=row[2],
                kind=EventKind(row[3]),
                payload=json.loads(row[4]),
                trust=Trust(row[5]),
            )
            for row in rows
        ]

    def task_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT task_id FROM events ORDER BY task_id").fetchall()
        return [row[0] for row in rows]

    def close(self) -> None:
        self._conn.close()
