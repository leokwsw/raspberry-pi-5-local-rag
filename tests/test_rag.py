from pathlib import Path

import pytest

from local_rag.database import Database
from local_rag.generation import EchoGenerator
from local_rag.rag import RagService, chunk_text


def test_chunks_overlap() -> None:
    assert chunk_text("abcdefghij", 6, 2) == ["abcdef", "efghij", "ij"]


@pytest.mark.asyncio
async def test_ingest_retrieve_answer_has_citation(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    rag = RagService(database, EchoGenerator())
    document_id = rag.ingest("facts.txt", "text/plain", "Raspberry Pi 5 has an ARM CPU.")
    answer, evidence = await rag.answer("What CPU?")
    assert evidence[0].document_id == document_id
    assert evidence[0].citation() in answer
    assert len(answer) < 2200


def test_web_distribution_is_mountable() -> None:
    assert (Path(__file__).parent.parent / "apps" / "web" / "index.html").is_file()


def test_reindex_updates_all_document_chunks(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    rag = RagService(database, EchoGenerator())
    document_id = rag.ingest("facts.txt", "text/plain", "A short fact.")
    assert rag.reindex(document_id) == 1
