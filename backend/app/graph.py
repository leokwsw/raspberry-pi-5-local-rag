"""Lightweight SQLite persistence for document knowledge triples."""

import sqlite3
from collections.abc import Iterable
from pathlib import Path


class KnowledgeGraphStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_triples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    UNIQUE(document_id, subject, predicate, object)
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_knowledge_triples_document ON knowledge_triples(document_id)"
            )

    def replace_document(self, document_id: str, filename: str, triples: Iterable[dict]) -> int:
        rows = [
            (
                document_id,
                filename,
                str(item["subject"]).strip(),
                str(item["predicate"]).strip(),
                str(item["object"]).strip(),
                int(item.get("chunk_index", 0)),
            )
            for item in triples
            if str(item.get("subject", "")).strip()
            and str(item.get("predicate", "")).strip()
            and str(item.get("object", "")).strip()
        ]
        with self._connect() as connection:
            connection.execute("DELETE FROM knowledge_triples WHERE document_id = ?", (document_id,))
            connection.executemany("""
                INSERT OR IGNORE INTO knowledge_triples
                    (document_id, filename, subject, predicate, object, chunk_index)
                VALUES (?, ?, ?, ?, ?, ?)
            """, rows)
            return int(connection.execute(
                "SELECT COUNT(*) FROM knowledge_triples WHERE document_id = ?", (document_id,)
            ).fetchone()[0])

    def delete_document(self, document_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM knowledge_triples WHERE document_id = ?", (document_id,))

    def document_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT document_id, COUNT(*) AS triple_count
                FROM knowledge_triples
                GROUP BY document_id
            """).fetchall()
        return {str(row["document_id"]): int(row["triple_count"]) for row in rows}

    def graph(self, document_id: str | None = None) -> dict:
        query = """
            SELECT id, document_id, filename, subject, predicate, object, chunk_index
            FROM knowledge_triples
        """
        parameters: tuple[str, ...] = ()
        if document_id:
            query += " WHERE document_id = ?"
            parameters = (document_id,)
        query += " ORDER BY subject COLLATE NOCASE, predicate COLLATE NOCASE, object COLLATE NOCASE"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        for row in rows:
            subject_id = self._node_id(str(row["subject"]))
            object_id = self._node_id(str(row["object"]))
            nodes.setdefault(subject_id, {"id": subject_id, "label": str(row["subject"])})
            nodes.setdefault(object_id, {"id": object_id, "label": str(row["object"])})
            edges.append({
                "id": str(row["id"]),
                "source": subject_id,
                "target": object_id,
                "predicate": str(row["predicate"]),
                "document_id": str(row["document_id"]),
                "filename": str(row["filename"]),
                "chunk_index": int(row["chunk_index"]),
            })
        return {"nodes": list(nodes.values()), "edges": edges}

    @staticmethod
    def _node_id(label: str) -> str:
        return " ".join(label.casefold().split())
