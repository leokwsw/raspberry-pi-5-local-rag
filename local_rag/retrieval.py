import importlib.util
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass

from local_rag.database import Database


def reciprocal_rank_fusion(rankings: Iterable[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, identifier in enumerate(ranking, 1):
            scores[identifier] = scores.get(identifier, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)


def bm25(database: Database, query: str, limit: int = 10) -> list[str]:
    terms = re.findall(r"[\w\u3400-\u9fff]+", query)
    if not terms:
        return []
    expression = " OR ".join(f'"{term}"' for term in terms)
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT c.id FROM chunks_fts f JOIN chunks c ON c.rowid=f.rowid "
            "WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (expression, limit),
        ).fetchall()
    return [str(row["id"]) for row in rows]


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_k: float
    reciprocal_rank: float
    ndcg: float


def evaluate(ranking: list[str], relevant: set[str], k: int = 10) -> RetrievalMetrics:
    top = ranking[:k]
    hits = [1 if item in relevant else 0 for item in top]
    recall = sum(hits) / len(relevant) if relevant else 0.0
    rr = next((1.0 / index for index, hit in enumerate(hits, 1) if hit), 0.0)
    dcg = sum(hit / math.log2(index + 1) for index, hit in enumerate(hits, 1))
    ideal = sum(1 / math.log2(index + 1) for index in range(1, min(k, len(relevant)) + 1))
    return RetrievalMetrics(recall, rr, dcg / ideal if ideal else 0.0)


def optional_backends() -> dict[str, str]:
    modules = {"sqlite-vec": "sqlite_vec", "faiss": "faiss", "qdrant": "qdrant_client",
               "lancedb": "lancedb"}
    return {name: "available" if importlib.util.find_spec(module) else "unavailable"
            for name, module in modules.items()}
