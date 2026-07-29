import json
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import psutil

from local_rag.benchmark import cpu_temperature
from local_rag.database import Database


class JobQueue:
    def __init__(self, database: Database) -> None:
        self.database = database

    def enqueue(self, kind: str, payload: dict[str, Any]) -> str:
        identifier, now = str(uuid.uuid4()), datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO jobs(id,type,status,payload,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?)",
                (identifier, kind, "queued", json.dumps(payload), now, now),
            )
        return identifier

    def claim(self) -> Optional[dict[str, Any]]:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE jobs SET status='running',attempts=attempts+1 WHERE id=?", (row["id"],)
                )
        return dict(row) if row else None

    def cancel(self, identifier: str) -> bool:
        with self.database.connect() as connection:
            result = connection.execute(
                "UPDATE jobs SET status='cancelled' WHERE id=? AND status='queued'", (identifier,)
            )
        return result.rowcount > 0

    def recover(self) -> int:
        with self.database.connect() as connection:
            result = connection.execute("UPDATE jobs SET status='queued' WHERE status='running'")
        return result.rowcount

    def list(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC"
            ).fetchall()]


def system_metrics(path: str = ".") -> dict[str, Any]:
    memory, disk = psutil.virtual_memory(), shutil.disk_usage(path)
    return {
        "cpu_percent": psutil.cpu_percent(),
        "ram_used": memory.used,
        "ram_available": memory.available,
        "disk_used": disk.used,
        "disk_free": disk.free,
        "temperature_c": cpu_temperature(),
    }


def ingestion_allowed(metrics: dict[str, Any]) -> bool:
    temperature = metrics.get("temperature_c")
    return metrics["ram_available"] > 1_000_000_000 and (
        temperature is None or float(temperature) < 80
    )
