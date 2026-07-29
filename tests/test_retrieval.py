from pathlib import Path

from local_rag.database import Database
from local_rag.generation import EchoGenerator
from local_rag.rag import RagService
from local_rag.retrieval import bm25, evaluate, reciprocal_rank_fusion


def test_bm25_and_fusion(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    rag = RagService(database, EchoGenerator())
    rag.ingest("pi.txt", "text/plain", "The Raspberry Pi uses an ARM processor.")
    result = bm25(database, "ARM processor")
    assert result
    assert reciprocal_rank_fusion([result, result]) == result
    assert evaluate(result, {result[0]}).recall_at_k == 1
