import hashlib
import json
import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import httpx

from local_rag.database import Database
from local_rag.generation import Generator


def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    step = max(1, size - overlap)
    return [clean[start : start + size] for start in range(0, len(clean), step)]


def parse_document(path: Path, media_type: str) -> str:
    if media_type == "application/pdf" or path.suffix.lower() == ".pdf":
        import fitz  # type: ignore[import-untyped]

        with fitz.open(path) as document:
            return "\n".join(page.get_text() for page in document)
    return path.read_text(encoding="utf-8")


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...


class HashEmbedder:
    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[\w\u3400-\u9fff]+", text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            vector[int.from_bytes(digest, "big") % self.dimensions] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class HttpEmbedder:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url, self.model = base_url.rstrip("/"), model

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self.base_url}/v1/embeddings",
            json={"model": self.model, "input": text},
            timeout=120,
        )
        response.raise_for_status()
        return [float(value) for value in response.json()["data"][0]["embedding"]]


def embed(text: str, dimensions: int = 256) -> list[float]:
    return HashEmbedder(dimensions).embed(text)


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    score: float
    source: str = "dense"

    def citation(self) -> str:
        return f"[{self.document_name}#{self.chunk_id[:8]}]"


class RagService:
    def __init__(
        self, database: Database, generator: Generator, embedder: Optional[Embedder] = None
    ) -> None:
        self.database, self.generator = database, generator
        self.embedder = embedder or HashEmbedder()

    def ingest(self, name: str, media_type: str, text: str) -> str:
        document_id = str(uuid.uuid4())
        chunks = chunk_text(text)
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?)",
                (document_id, name, media_type, now, "ready"),
            )
            for index, value in enumerate(chunks):
                connection.execute(
                    "INSERT INTO chunks VALUES(?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), document_id, index, value, len(value.split()),
                     json.dumps({}), json.dumps(self.embedder.embed(value))),
                )
        return document_id

    def documents(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id,name,media_type,created_at,status FROM documents "
                "ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, document_id: str) -> bool:
        with self.database.connect() as connection:
            result = connection.execute("DELETE FROM documents WHERE id=?", (document_id,))
        return result.rowcount > 0

    def reindex(self, document_id: str) -> int:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT id,text FROM chunks WHERE document_id=?", (document_id,)
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE chunks SET embedding=? WHERE id=?",
                    (json.dumps(self.embedder.embed(row["text"])), row["id"]),
                )
        return len(rows)

    def retrieve(self, query: str, limit: int = 5) -> list[Evidence]:
        query_vector = self.embedder.embed(query)
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT c.id,c.document_id,d.name,c.text,c.embedding "
                "FROM chunks c JOIN documents d ON d.id=c.document_id"
            ).fetchall()
        evidence = [
            Evidence(
                row["id"], row["document_id"], row["name"], row["text"],
                sum(a * b for a, b in zip(query_vector, json.loads(row["embedding"]))),
            )
            for row in rows
        ]
        ranked = sorted(evidence, key=lambda item: item.score, reverse=True)
        return [item for item in ranked if item.score > 0.05][:limit]

    async def answer(self, question: str) -> tuple[str, list[Evidence]]:
        retrieved = self.retrieve(question, limit=3)
        evidence: list[Evidence] = []
        context_parts: list[str] = []
        remaining = 1800
        for item in retrieved:
            prefix = f"{item.citation()} "
            available = remaining - len(prefix)
            if available < 100:
                break
            context_parts.append(prefix + item.text[:available])
            evidence.append(item)
            remaining -= len(context_parts[-1])
        context = "\n".join(context_parts)
        prompt = (
            "Answer only from the context. Preserve source citations. "
            f"If insufficient, say so.\n\nContext:\n{context}\n\nQuestion: {question}"
        )
        return await self.generator.generate(prompt), evidence
