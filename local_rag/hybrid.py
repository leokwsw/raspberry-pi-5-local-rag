import re
from dataclasses import dataclass

from local_rag.database import Database
from local_rag.graph import GraphStore
from local_rag.rag import Evidence, RagService
from local_rag.retrieval import bm25, reciprocal_rank_fusion


@dataclass(frozen=True)
class HybridResult:
    evidence: list[Evidence]
    trace: dict[str, list[str]]


class HybridRetriever:
    def __init__(self, database: Database, rag: RagService, graph: GraphStore) -> None:
        self.database, self.rag, self.graph = database, rag, graph

    def retrieve(self, query: str, limit: int = 8) -> HybridResult:
        dense = self.rag.retrieve(query, limit)
        dense_ids = [item.chunk_id for item in dense]
        keyword_ids = bm25(self.database, query, limit)
        graph_ids: list[str] = []
        for term in re.findall(r"[\w\u3400-\u9fff]+", query.casefold()):
            for entity in self.graph.search(term):
                graph_ids.extend(
                    str(edge["source_chunk_id"]) for edge in self.graph.neighbours(entity["id"])
                )
        ranking = reciprocal_rank_fusion([dense_ids, keyword_ids, graph_ids])[:limit]
        by_id = {item.chunk_id: item for item in dense}
        missing = [identifier for identifier in ranking if identifier not in by_id]
        if missing:
            with self.database.connect() as connection:
                for identifier in missing:
                    row = connection.execute(
                        "SELECT c.id,c.document_id,d.name,c.text FROM chunks c "
                        "JOIN documents d ON d.id=c.document_id WHERE c.id=?",
                        (identifier,),
                    ).fetchone()
                    if row:
                        by_id[identifier] = Evidence(
                            row["id"], row["document_id"], row["name"], row["text"], 0, "graph"
                        )
        return HybridResult(
            [by_id[item] for item in ranking if item in by_id],
            {"dense": dense_ids, "bm25": keyword_ids, "graph": graph_ids, "fused": ranking},
        )
