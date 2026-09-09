"""Dedupe tests — a redelivered message id must never look new.

The property under test is the one the customer feels: ask once, get answered
once. Every test here runs without HTTP, without Meta and without a brain,
because the guarantee is the database's and should be provable on its own.
"""
import sqlite3
import threading

from application.data_repositories.seen_message_repository import SeenMessageRepository


def _repo(tmp_path, name="whatsapp.db"):
    return SeenMessageRepository(str(tmp_path / name))


def test_first_sighting_is_new_and_the_second_is_not(tmp_path):
    repo = _repo(tmp_path)
    assert repo.mark_seen("wamid.AAA") is True
    assert repo.mark_seen("wamid.AAA") is False


def test_different_ids_are_independent(tmp_path):
    repo = _repo(tmp_path)
    assert repo.mark_seen("wamid.AAA") is True
    assert repo.mark_seen("wamid.BBB") is True


def test_the_database_holds_the_answer_not_the_instance(tmp_path):
    """A restart mid-retry-window must still refuse the redelivery.

    Proven by asking a *second* repository object on the same file, which is what
    a restarted process is.
    """
    assert _repo(tmp_path).mark_seen("wamid.AAA") is True
    assert _repo(tmp_path).mark_seen("wamid.AAA") is False


def test_concurrent_deliveries_produce_exactly_one_new(tmp_path):
    """Eight threads, one id, exactly one winner.

    This asserts the invariant a customer feels — asked once, answered once —
    under real concurrency. It is deliberately *not* claimed as proof that
    ``INSERT OR IGNORE`` is the only way to get there: a check-then-act version
    wrapped in an ``IntegrityError`` fallback was measured returning exactly one
    'new' as well, because SQLite's write lock serialises the inserts anyway.
    What actually rests on the schema is covered by the primary-key test below.
    """
    repo = _repo(tmp_path)
    results: list[bool] = []
    lock = threading.Lock()
    start = threading.Barrier(8)

    def attempt():
        start.wait()
        outcome = repo.mark_seen("wamid.RACE")
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 8
    assert sum(results) == 1, f"expected exactly one 'new', got {sum(results)}"


def test_purge_removes_only_aged_rows(tmp_path):
    repo = _repo(tmp_path)
    now = 1_000_000
    repo.mark_seen("wamid.OLD", now=now - 200)
    repo.mark_seen("wamid.NEW", now=now - 10)

    removed = repo.purge_older_than(retention_seconds=100, now=now)

    assert removed == 1
    assert repo.get("wamid.OLD") is None
    assert repo.get("wamid.NEW") is not None


def test_purge_on_an_empty_table_is_harmless(tmp_path):
    assert _repo(tmp_path).purge_older_than() == 0


def test_a_purged_id_is_new_again(tmp_path):
    """Retention is a promise about storage, not about correctness forever.

    Long after Meta has stopped retrying, forgetting an id is the point.
    """
    repo = _repo(tmp_path)
    now = 1_000_000
    repo.mark_seen("wamid.AAA", now=now - 200)
    repo.purge_older_than(retention_seconds=100, now=now)
    assert repo.mark_seen("wamid.AAA", now=now) is True


def test_schema_survives_reopening(tmp_path):
    """Constructing over an existing file must not wipe or fail."""
    path = tmp_path / "whatsapp.db"
    SeenMessageRepository(str(path)).mark_seen("wamid.AAA")
    SeenMessageRepository(str(path))  # second construction, same file
    assert SeenMessageRepository(str(path)).mark_seen("wamid.AAA") is False


def test_the_primary_key_is_what_enforces_uniqueness(tmp_path):
    """Negative control: without the constraint these tests would pass anyway.

    Inserting the same id twice without OR IGNORE must raise, proving the
    uniqueness lives in the schema rather than in mark_seen's Python.
    """
    path = tmp_path / "whatsapp.db"
    SeenMessageRepository(str(path))
    conn = sqlite3.connect(str(path))
    conn.execute("INSERT INTO seen_message (wamid, seen_at) VALUES ('x', 1)")
    try:
        raised = False
        try:
            conn.execute("INSERT INTO seen_message (wamid, seen_at) VALUES ('x', 2)")
        except sqlite3.IntegrityError:
            raised = True
        assert raised, "no PRIMARY KEY constraint — dedupe would rest on nothing"
    finally:
        conn.close()
