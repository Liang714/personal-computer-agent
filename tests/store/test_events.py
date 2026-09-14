import sqlite3
from pathlib import Path

import pytest

from pca.core.provenance import Trust
from pca.store.events import EventKind, EventStore


@pytest.fixture
def store(tmp_path: Path) -> EventStore:
    return EventStore(tmp_path / "audit.sqlite3")


def test_append_assigns_monotonic_sequence_per_task(store: EventStore) -> None:
    a = store.append("t1", EventKind.TASK_STARTED, {"goal": "g"})
    b = store.append("t1", EventKind.OBSERVED, {})
    assert (a.seq, b.seq) == (1, 2)


def test_sequences_are_independent_across_tasks(store: EventStore) -> None:
    store.append("t1", EventKind.TASK_STARTED, {})
    first_of_t2 = store.append("t2", EventKind.TASK_STARTED, {})
    assert first_of_t2.seq == 1


def test_events_round_trip_in_order(store: EventStore) -> None:
    store.append("t1", EventKind.TASK_STARTED, {"goal": "organise"})
    store.append("t1", EventKind.PLANNED, {"tool": "filesystem.list"})
    events = store.events("t1")
    assert [e.kind for e in events] == [EventKind.TASK_STARTED, EventKind.PLANNED]
    assert events[0].payload["goal"] == "organise"


def test_trust_is_persisted(store: EventStore) -> None:
    store.append("t1", EventKind.ACTION_EXECUTED, {}, trust=Trust.EXTERNAL_CONTENT)
    assert store.events("t1")[0].trust is Trust.EXTERNAL_CONTENT


def test_log_is_append_only(store: EventStore, tmp_path: Path) -> None:
    store.append("t1", EventKind.TASK_STARTED, {})
    conn = sqlite3.connect(tmp_path / "audit.sqlite3")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE events SET kind = 'tampered' WHERE task_id = 't1'")
    conn.close()


def test_deletes_are_also_rejected(store: EventStore, tmp_path: Path) -> None:
    store.append("t1", EventKind.TASK_STARTED, {})
    conn = sqlite3.connect(tmp_path / "audit.sqlite3")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM events WHERE task_id = 't1'")
    conn.close()
