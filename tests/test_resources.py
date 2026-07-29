from pathlib import Path

from local_rag.database import Database
from local_rag.resources import JobQueue, ingestion_allowed


def test_queue_claim_cancel_and_recover(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    queue = JobQueue(database)
    first = queue.enqueue("embed", {})
    assert queue.claim()["id"] == first
    assert queue.recover() == 1
    second = queue.enqueue("index", {})
    assert queue.cancel(second)
    assert not ingestion_allowed({"ram_available": 1, "temperature_c": 50})
