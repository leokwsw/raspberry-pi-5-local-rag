import importlib.util
import uuid
from typing import Any

from local_rag.database import Database
from local_rag.extraction import Triple


class GraphStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def _entity(self, connection: Any, name: str, kind: str = "unknown") -> str:
        row = connection.execute(
            "SELECT id FROM entities WHERE canonical_name=?", (name,)
        ).fetchone()
        if row:
            return str(row["id"])
        identifier = str(uuid.uuid4())
        connection.execute("INSERT INTO entities VALUES(?,?,?)", (identifier, name, kind))
        return identifier

    def add(self, triple: Triple) -> str:
        with self.database.connect() as connection:
            subject = self._entity(connection, triple.subject)
            object_id = self._entity(connection, triple.object)
            identifier = str(uuid.uuid4())
            connection.execute(
                "INSERT OR IGNORE INTO relationships VALUES(?,?,?,?,?,?)",
                (identifier, subject, triple.predicate, object_id, triple.chunk_id,
                 triple.confidence),
            )
        return identifier

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM entities WHERE canonical_name LIKE ? LIMIT ?",
                (f"%{query.casefold()}%", limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def neighbours(self, entity_id: str) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT r.*,s.canonical_name subject,o.canonical_name object,c.text source_text "
                "FROM relationships r JOIN entities s ON s.id=r.subject_id "
                "JOIN entities o ON o.id=r.object_id JOIN chunks c ON c.id=r.source_chunk_id "
                "WHERE r.subject_id=? OR r.object_id=?",
                (entity_id, entity_id),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def capabilities() -> dict[str, str]:
        return {
            "sqlite": "available",
            "arangodb": "available" if importlib.util.find_spec("arango") else "unavailable",
        }
