import json
import uuid
from datetime import datetime, timezone
from typing import Any

from local_rag.database import Database
from local_rag.generation import Generator


class GraphRagResearch:
    def __init__(self, database: Database, generator: Generator) -> None:
        self.database, self.generator = database, generator

    def communities(self) -> list[set[str]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT subject_id,object_id FROM relationships"
            ).fetchall()
        adjacency: dict[str, set[str]] = {}
        for row in rows:
            adjacency.setdefault(row["subject_id"], set()).add(row["object_id"])
            adjacency.setdefault(row["object_id"], set()).add(row["subject_id"])
        result: list[set[str]] = []
        unseen = set(adjacency)
        while unseen:
            pending, group = [unseen.pop()], set()
            while pending:
                node = pending.pop()
                group.add(node)
                neighbours = adjacency.get(node, set()) & unseen
                unseen -= neighbours
                pending.extend(neighbours)
            result.append(group)
        return result

    async def summarize(self) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        with self.database.connect() as connection:
            for members in self.communities():
                placeholders = ",".join("?" for _ in members)
                rows = connection.execute(
                    f"SELECT canonical_name FROM entities WHERE id IN ({placeholders})",
                    tuple(members),
                ).fetchall()
                names = [row["canonical_name"] for row in rows]
                summary = await self.generator.generate(
                    "Summarize this graph community using only these entities: " + ", ".join(names)
                )
                identifier, now = str(uuid.uuid4()), datetime.now(timezone.utc).isoformat()
                connection.execute(
                    "INSERT OR REPLACE INTO graph_communities VALUES(?,?,?,?)",
                    (identifier, json.dumps(sorted(members)), summary, now),
                )
                output.append({"id": identifier, "members": names, "summary": summary})
        return output

    def global_context(self, limit: int = 5) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT summary FROM graph_communities WHERE summary IS NOT NULL LIMIT ?", (limit,)
            ).fetchall()
        return [str(row["summary"]) for row in rows]
