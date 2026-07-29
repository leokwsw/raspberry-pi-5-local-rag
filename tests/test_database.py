from pathlib import Path

from local_rag.database import SCHEMA_VERSION, Database


def test_fresh_database_migrates(tmp_path: Path) -> None:
    database = Database(tmp_path / "rag.db")
    database.migrate()
    with database.connect() as connection:
        version = connection.execute("SELECT version FROM schema_version").fetchone()[0]
    assert version == SCHEMA_VERSION
