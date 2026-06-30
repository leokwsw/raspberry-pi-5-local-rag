"""
Storage layer for enhanced RAG application.
Handles conversation history, feedback, graph database, and document management.
Designed for lightweight operation on Raspberry Pi 5.
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


DEFAULT_STORAGE_PATH = "./rag_storage"


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    sources: list[dict] = field(default_factory=list)
    feedback: Optional[str] = None  # "positive", "negative", or None


@dataclass
class Conversation:
    id: str
    title: str
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Document:
    id: str
    filename: str
    content_type: str  # "text", "audio", "video"
    text_content: str
    source_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    chunk_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Feedback:
    id: str
    question: str
    answer: str
    rating: str  # "positive" or "negative"
    comment: Optional[str] = None
    source_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Entity:
    id: str
    name: str
    entity_type: str  # "concept", "person", "organization", "location", etc.
    description: Optional[str] = None
    document_ids: list[str] = field(default_factory=list)


@dataclass
class Relationship:
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # "related_to", "part_of", "causes", etc.
    weight: float = 1.0
    document_ids: list[str] = field(default_factory=list)


class StorageManager:
    """SQLite-based storage manager for conversations, feedback, documents, and graph."""

    def __init__(self, storage_path: str = DEFAULT_STORAGE_PATH):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_path / "rag_data.db"
        self._init_database()

    def _init_database(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    sources TEXT,
                    feedback TEXT,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    text_content TEXT NOT NULL,
                    source_path TEXT,
                    created_at TEXT NOT NULL,
                    chunk_ids TEXT,
                    metadata TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    comment TEXT,
                    source_ids TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    description TEXT,
                    document_ids TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    document_ids TEXT,
                    FOREIGN KEY (source_entity_id) REFERENCES entities(id),
                    FOREIGN KEY (target_entity_id) REFERENCES entities(id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_entity_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_entity_id)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()

    # Conversation methods
    def create_conversation(self, title: str = "New Chat") -> Conversation:
        conv = Conversation(
            id=str(uuid.uuid4()),
            title=title,
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv.id, conv.title, conv.created_at, conv.updated_at),
            )
            conn.commit()
        return conv

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            conv = Conversation(
                id=row[0],
                title=row[1],
                created_at=row[2],
                updated_at=row[3],
            )

            cursor.execute(
                "SELECT role, content, timestamp, sources, feedback FROM messages WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            )
            for msg_row in cursor.fetchall():
                sources = json.loads(msg_row[3]) if msg_row[3] else []
                conv.messages.append(
                    Message(
                        role=msg_row[0],
                        content=msg_row[1],
                        timestamp=msg_row[2],
                        sources=sources,
                        feedback=msg_row[4],
                    )
                )
            return conv

    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            conversations = []
            for row in cursor.fetchall():
                conversations.append(
                    Conversation(
                        id=row[0],
                        title=row[1],
                        created_at=row[2],
                        updated_at=row[3],
                    )
                )
            return conversations

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict] = None,
    ) -> Message:
        message = Message(
            role=role,
            content=content,
            sources=sources or [],
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp, sources, feedback) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    message.role,
                    message.content,
                    message.timestamp,
                    json.dumps(message.sources),
                    message.feedback,
                ),
            )
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), conversation_id),
            )
            conn.commit()
        return message

    def update_conversation_title(self, conversation_id: str, title: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (title, datetime.now().isoformat(), conversation_id),
            )
            conn.commit()

    def delete_conversation(self, conversation_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()

    # Document methods
    def add_document(self, doc: Document) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO documents 
                   (id, filename, content_type, text_content, source_path, created_at, chunk_ids, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    doc.id,
                    doc.filename,
                    doc.content_type,
                    doc.text_content,
                    doc.source_path,
                    doc.created_at,
                    json.dumps(doc.chunk_ids),
                    json.dumps(doc.metadata),
                ),
            )
            conn.commit()

    def get_document(self, doc_id: str) -> Optional[Document]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Document(
                id=row[0],
                filename=row[1],
                content_type=row[2],
                text_content=row[3],
                source_path=row[4],
                created_at=row[5],
                chunk_ids=json.loads(row[6]) if row[6] else [],
                metadata=json.loads(row[7]) if row[7] else {},
            )

    def list_documents(self, content_type: Optional[str] = None) -> list[Document]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if content_type:
                cursor.execute(
                    "SELECT * FROM documents WHERE content_type = ? ORDER BY created_at DESC",
                    (content_type,),
                )
            else:
                cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
            documents = []
            for row in cursor.fetchall():
                documents.append(
                    Document(
                        id=row[0],
                        filename=row[1],
                        content_type=row[2],
                        text_content=row[3],
                        source_path=row[4],
                        created_at=row[5],
                        chunk_ids=json.loads(row[6]) if row[6] else [],
                        metadata=json.loads(row[7]) if row[7] else {},
                    )
                )
            return documents

    def delete_document(self, doc_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()

    # Feedback methods
    def add_feedback(self, feedback: Feedback) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO feedback 
                   (id, question, answer, rating, comment, source_ids, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    feedback.id,
                    feedback.question,
                    feedback.answer,
                    feedback.rating,
                    feedback.comment,
                    json.dumps(feedback.source_ids),
                    feedback.created_at,
                ),
            )
            conn.commit()

    def get_feedback_for_sources(self, source_ids: list[str]) -> list[Feedback]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
            feedbacks = []
            for row in cursor.fetchall():
                fb_source_ids = json.loads(row[5]) if row[5] else []
                if any(sid in fb_source_ids for sid in source_ids):
                    feedbacks.append(
                        Feedback(
                            id=row[0],
                            question=row[1],
                            answer=row[2],
                            rating=row[3],
                            comment=row[4],
                            source_ids=fb_source_ids,
                            created_at=row[6],
                        )
                    )
            return feedbacks

    def get_source_feedback_scores(self) -> dict[str, float]:
        """Calculate feedback scores for sources. Positive = +1, Negative = -1."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_ids, rating FROM feedback")
            scores: dict[str, float] = {}
            for row in cursor.fetchall():
                source_ids = json.loads(row[0]) if row[0] else []
                rating = row[1]
                delta = 1.0 if rating == "positive" else -1.0
                for sid in source_ids:
                    scores[sid] = scores.get(sid, 0.0) + delta
            return scores

    def list_feedback(self, limit: int = 100) -> list[Feedback]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,))
            feedbacks = []
            for row in cursor.fetchall():
                feedbacks.append(
                    Feedback(
                        id=row[0],
                        question=row[1],
                        answer=row[2],
                        rating=row[3],
                        comment=row[4],
                        source_ids=json.loads(row[5]) if row[5] else [],
                        created_at=row[6],
                    )
                )
            return feedbacks

    # Graph DB methods (Entity and Relationship)
    def add_entity(self, entity: Entity) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO entities 
                   (id, name, entity_type, description, document_ids) 
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    entity.id,
                    entity.name,
                    entity.entity_type,
                    entity.description,
                    json.dumps(entity.document_ids),
                ),
            )
            conn.commit()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Entity(
                id=row[0],
                name=row[1],
                entity_type=row[2],
                description=row[3],
                document_ids=json.loads(row[4]) if row[4] else [],
            )

    def find_entity_by_name(self, name: str) -> Optional[Entity]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return Entity(
                id=row[0],
                name=row[1],
                entity_type=row[2],
                description=row[3],
                document_ids=json.loads(row[4]) if row[4] else [],
            )

    def list_entities(self, entity_type: Optional[str] = None) -> list[Entity]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if entity_type:
                cursor.execute("SELECT * FROM entities WHERE entity_type = ?", (entity_type,))
            else:
                cursor.execute("SELECT * FROM entities")
            entities = []
            for row in cursor.fetchall():
                entities.append(
                    Entity(
                        id=row[0],
                        name=row[1],
                        entity_type=row[2],
                        description=row[3],
                        document_ids=json.loads(row[4]) if row[4] else [],
                    )
                )
            return entities

    def add_relationship(self, rel: Relationship) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO relationships 
                   (id, source_entity_id, target_entity_id, relationship_type, weight, document_ids) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    rel.id,
                    rel.source_entity_id,
                    rel.target_entity_id,
                    rel.relationship_type,
                    rel.weight,
                    json.dumps(rel.document_ids),
                ),
            )
            conn.commit()

    def get_relationships_for_entity(self, entity_id: str) -> list[Relationship]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?",
                (entity_id, entity_id),
            )
            relationships = []
            for row in cursor.fetchall():
                relationships.append(
                    Relationship(
                        id=row[0],
                        source_entity_id=row[1],
                        target_entity_id=row[2],
                        relationship_type=row[3],
                        weight=row[4],
                        document_ids=json.loads(row[5]) if row[5] else [],
                    )
                )
            return relationships

    def get_related_entities(self, entity_id: str, max_depth: int = 2) -> list[tuple[Entity, int]]:
        """Get related entities up to max_depth hops away. Returns (entity, depth) tuples."""
        visited = {entity_id}
        result = []
        current_level = [entity_id]

        for depth in range(1, max_depth + 1):
            next_level = []
            for eid in current_level:
                rels = self.get_relationships_for_entity(eid)
                for rel in rels:
                    other_id = rel.target_entity_id if rel.source_entity_id == eid else rel.source_entity_id
                    if other_id not in visited:
                        visited.add(other_id)
                        entity = self.get_entity(other_id)
                        if entity:
                            result.append((entity, depth))
                            next_level.append(other_id)
            current_level = next_level

        return result

    def delete_entity(self, entity_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?",
                (entity_id, entity_id),
            )
            cursor.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
            conn.commit()

    # Settings methods
    def get_setting(self, key: str, default: str = "") -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def get_stats(self) -> dict:
        """Get storage statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            stats = {}
            cursor.execute("SELECT COUNT(*) FROM conversations")
            stats["conversations"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats["messages"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM documents")
            stats["documents"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM feedback")
            stats["feedback"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM entities")
            stats["entities"] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM relationships")
            stats["relationships"] = cursor.fetchone()[0]
            return stats
