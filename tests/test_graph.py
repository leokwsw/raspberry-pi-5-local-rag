from pathlib import Path

from local_rag.database import Database
from local_rag.extraction import Triple
from local_rag.generation import EchoGenerator
from local_rag.graph import GraphStore
from local_rag.rag import RagService


def test_graph_relationship_keeps_source(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    rag = RagService(database, EchoGenerator())
    rag.ingest("pi.txt", "text/plain", "Pi uses ARM")
    chunk = rag.retrieve("ARM")[0]
    graph = GraphStore(database)
    graph.add(Triple("pi", "uses", "arm", 1, chunk.chunk_id, chunk.text))
    entity = graph.search("pi")[0]
    assert graph.neighbours(entity["id"])[0]["source_chunk_id"] == chunk.chunk_id
