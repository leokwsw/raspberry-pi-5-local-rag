from pathlib import Path

import pytest

from local_rag.database import Database
from local_rag.extraction import Triple
from local_rag.generation import EchoGenerator
from local_rag.graph import GraphStore
from local_rag.graphrag import GraphRagResearch
from local_rag.rag import RagService


@pytest.mark.asyncio
async def test_community_summary_is_precomputed(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    rag, graph = RagService(database, EchoGenerator()), GraphStore(database)
    rag.ingest("pi.txt", "text/plain", "Pi uses ARM")
    source = rag.retrieve("ARM")[0]
    graph.add(Triple("pi", "uses", "arm", 1, source.chunk_id, source.text))
    research = GraphRagResearch(database, EchoGenerator())
    assert len(research.communities()) == 1
    assert await research.summarize()
    assert research.global_context()
