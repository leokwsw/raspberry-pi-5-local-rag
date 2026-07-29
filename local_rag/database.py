import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 2
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
INSERT INTO schema_version(version)
SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM schema_version);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS benchmark_runs(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
 started_at TEXT NOT NULL, finished_at TEXT, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, media_type TEXT NOT NULL,
 created_at TEXT NOT NULL, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks(
 id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 chunk_index INTEGER NOT NULL, text TEXT NOT NULL, token_count INTEGER NOT NULL,
 metadata TEXT NOT NULL, embedding TEXT NOT NULL
);
UPDATE schema_version SET version=2;
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()
