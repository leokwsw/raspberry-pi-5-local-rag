from pathlib import Path

from local_rag.database import Database
from local_rag.extraction import Triple
from local_rag.generation import EchoGenerator
from local_rag.graph import GraphStore
from local_rag.hybrid import HybridRetriever
from local_rag.rag import RagService


def test_graph_assisted_evidence_has_source_chunk(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    rag, graph = RagService(database, EchoGenerator()), GraphStore(database)
    rag.ingest("pi.txt", "text/plain", "Pi architecture facts.")
    source = rag.retrieve("facts")[0]
    graph.add(Triple("pi", "uses", "arm", 1, source.chunk_id, source.text))
    result = HybridRetriever(database, rag, graph).retrieve("pi")
    assert source.chunk_id in result.trace["graph"]
    assert all(item.chunk_id for item in result.evidence)
