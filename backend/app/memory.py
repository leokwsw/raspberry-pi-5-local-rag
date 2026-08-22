import sqlite3
from pathlib import Path
from threading import Lock
from uuid import uuid4


class ConversationMemory:
    def __init__(self, path: str, max_messages: int = 12) -> None:
        self.path = path
        self.max_messages = max_messages
        self.lock = Lock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS messages_session ON messages(session_id, id)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def new_session_id(self) -> str:
        return str(uuid4())

    def recent(self, session_id: str, limit: int | None = None) -> list[dict]:
        maximum = limit or self.max_messages
        with self.lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, maximum),
            ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]

    def append_exchange(self, session_id: str, question: str, answer: str) -> None:
        with self.lock, self._connect() as connection:
            connection.executemany(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                [(session_id, "user", question), (session_id, "assistant", answer)],
            )
            connection.execute("""
                DELETE FROM messages WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?
                )
            """, (session_id, session_id, self.max_messages))

    def clear(self, session_id: str) -> None:
        with self.lock, self._connect() as connection:
            connection.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
