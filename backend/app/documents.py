"""Persistent staging area for uploaded documents and extracted triples."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class DocumentRegistry:
    def __init__(self, database_path: str, upload_dir: str) -> None:
        self.database_path = database_path
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    chunks_json TEXT,
                    triples_json TEXT,
                    embeddings_ready INTEGER NOT NULL DEFAULT 0,
                    triples_ready INTEGER NOT NULL DEFAULT 0,
                    graph_stored INTEGER NOT NULL DEFAULT 0
                )
            """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def add(self, document_id: str, filename: str, content: bytes) -> dict:
        path = self.upload_dir / document_id
        path.write_bytes(content)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO documents(document_id, filename, size, path) VALUES (?, ?, ?, ?)",
                (document_id, filename, len(content), str(path)),
            )
        return self.get(document_id)

    def get(self, document_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,)).fetchone()
        if row is None:
            raise KeyError(document_id)
        return self._serialize(row)

    def list(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM documents ORDER BY lower(filename)").fetchall()
        return [self._serialize(row) for row in rows]

    def update_chunks(self, document_id: str, chunks: list[dict]) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE documents SET chunks_json = ? WHERE document_id = ?",
                               (json.dumps(chunks, ensure_ascii=False), document_id))

    def update_processing(self, document_id: str, *, embeddings_ready: bool | None = None,
                          triples: list[dict] | None = None) -> None:
        assignments: list[str] = []
        values: list[object] = []
        if embeddings_ready is not None:
            assignments.append("embeddings_ready = ?")
            values.append(int(embeddings_ready))
        if triples is not None:
            assignments.extend(("triples_json = ?", "triples_ready = 1", "graph_stored = 0"))
            values.append(json.dumps(triples, ensure_ascii=False))
        if not assignments:
            return
        values.append(document_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE documents SET {', '.join(assignments)} WHERE document_id = ?", values)

    def mark_graph_stored(self, document_id: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE documents SET graph_stored = 1 WHERE document_id = ?", (document_id,))

    def delete(self, document_id: str) -> None:
        try:
            item = self.get(document_id)
        except KeyError:
            return
        Path(item["path"]).unlink(missing_ok=True)
        with self._connect() as connection:
            connection.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))

    @staticmethod
    def _serialize(row: sqlite3.Row) -> dict:
        chunks = json.loads(row["chunks_json"]) if row["chunks_json"] else []
        triples = json.loads(row["triples_json"]) if row["triples_json"] else []
        return {
            "document_id": row["document_id"], "filename": row["filename"], "size": row["size"],
            "path": row["path"], "chunks": chunks, "triples": triples,
            "chunk_count": len(chunks), "graph_triple_count": len(triples),
            "embeddings_ready": bool(row["embeddings_ready"]),
            "triples_ready": bool(row["triples_ready"]), "graph_stored": bool(row["graph_stored"]),
        }
