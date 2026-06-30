"""
Enhanced RAG engine with Graph DB and Feedback RAG support.
Designed for Raspberry Pi 5 16GB.
"""

import re
import textwrap
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from storage import (
    StorageManager,
    Document,
    Entity,
    Relationship,
    Feedback,
    DEFAULT_STORAGE_PATH,
)
from media_processor import MediaProcessor, TextChunker


DEFAULT_DB_PATH = "./chroma_db"
DEFAULT_COLLECTION = "pi_local_rag"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_GENERATION_MODEL = "llama3.2:3b"


KNOWLEDGE_BASE = [
    {
        "id": "pi5-memory",
        "title": "Raspberry Pi 5 memory",
        "text": "Raspberry Pi 5 有 4GB、8GB 與 16GB RAM 版本。16GB 版本更適合小型本機 AI、RAG、資料庫與多服務同時運行。",
    },
    {
        "id": "pi5-cpu",
        "title": "Raspberry Pi 5 processor",
        "text": "Raspberry Pi 5 使用 Broadcom BCM2712 四核心 Arm Cortex-A76 處理器，時脈 2.4GHz，CPU 效能明顯高於 Raspberry Pi 4。",
    },
    {
        "id": "pi5-cooling",
        "title": "Raspberry Pi 5 cooling",
        "text": "在 Raspberry Pi 5 上長時間執行 LLM 或 embedding 任務時，建議使用主動散熱器，避免過熱造成降頻與回應變慢。",
    },
    {
        "id": "ollama-purpose",
        "title": "Ollama local models",
        "text": "Ollama 可以在本機執行大型語言模型與 embedding 模型，適合邊緣裝置、離線開發與不想把資料送到雲端的 RAG 應用。",
    },
    {
        "id": "chromadb-purpose",
        "title": "ChromaDB vector store",
        "text": "ChromaDB 是輕量向量資料庫，可在本機儲存文件 embedding，並依照語意相似度找回和問題最相關的內容。",
    },
    {
        "id": "rag-flow",
        "title": "RAG workflow",
        "text": "RAG 流程通常包含文件切分、embedding、向量儲存、檢索相關內容、把 context 放進 prompt，最後由 LLM 根據資料回答。",
    },
    {
        "id": "model-choice",
        "title": "Model choice on Raspberry Pi 5",
        "text": "Raspberry Pi 5 16GB 可優先使用 llama3.2:3b 這類較小模型取得較快回應；較大的 7B 或 8B 模型可能可用，但延遲會增加。",
    },
]


@dataclass
class RetrievedSource:
    id: str
    title: str
    text: str
    distance: Optional[float] = None
    feedback_score: float = 0.0
    adjusted_score: float = 0.0
    graph_boost: float = 0.0


@dataclass
class GraphContext:
    """Additional context from knowledge graph."""
    entities: list[Entity] = field(default_factory=list)
    relationships: list[tuple[str, str, str]] = field(default_factory=list)


class EnhancedRAG:
    """Enhanced RAG with Graph DB and Feedback support."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        collection_name: str = DEFAULT_COLLECTION,
        embed_model: str = DEFAULT_EMBED_MODEL,
        generation_model: str = DEFAULT_GENERATION_MODEL,
        top_k: int = 3,
        storage_path: str = DEFAULT_STORAGE_PATH,
        use_feedback: bool = True,
        use_graph: bool = True,
        feedback_weight: float = 0.1,
        graph_weight: float = 0.05,
    ) -> None:
        self.db_path = db_path
        self.collection_name = collection_name
        self.embed_model = embed_model
        self.generation_model = generation_model
        self.top_k = max(1, top_k)
        self.use_feedback = use_feedback
        self.use_graph = use_graph
        self.feedback_weight = feedback_weight
        self.graph_weight = graph_weight

        try:
            import chromadb
            import ollama
        except ModuleNotFoundError as exc:
            raise RuntimeError("Missing Python dependency. Run: pip install -r requirements.txt") from exc

        self.ollama = ollama
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name=collection_name)

        self.storage = StorageManager(storage_path)
        self.media_processor = MediaProcessor()
        self.chunker = TextChunker(chunk_size=500, chunk_overlap=50)

    def prepare(self, rebuild: bool = False) -> None:
        """Initialize or rebuild the knowledge base."""
        if rebuild:
            try:
                self.client.delete_collection(name=self.collection_name)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(name=self.collection_name)

        if self.collection.count() == 0:
            self._index_default_knowledge()

    def _index_default_knowledge(self) -> None:
        """Index the default knowledge base."""
        documents = []
        for item in KNOWLEDGE_BASE:
            documents.append({
                "id": item["id"],
                "text": item["text"],
                "title": item["title"],
            })
        self._index_documents(documents)

        if self.use_graph:
            self._extract_entities_from_knowledge_base()

    def _index_documents(self, documents: list[dict]) -> None:
        """Index documents into ChromaDB."""
        ids = []
        texts = []
        embeddings = []
        metadatas = []

        for doc in documents:
            ids.append(doc["id"])
            texts.append(doc["text"])
            embeddings.append(self.embed(doc["text"]))
            metadatas.append({"title": doc.get("title", "Untitled")})

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        response = self.ollama.embeddings(model=self.embed_model, prompt=text)
        return response["embedding"]

    def add_document(self, filepath: str) -> Document:
        """Add a document from file."""
        doc = self.media_processor.create_document(filepath)
        self.storage.add_document(doc)

        chunks = self.chunker.chunk_document(doc)
        chunk_ids = []

        for chunk in chunks:
            chunk_ids.append(chunk["id"])
            self.collection.upsert(
                ids=[chunk["id"]],
                documents=[chunk["text"]],
                embeddings=[self.embed(chunk["text"])],
                metadatas=[{
                    "title": f"{doc.filename} (chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']})",
                    "document_id": doc.id,
                    "chunk_index": chunk["chunk_index"],
                }],
            )

        doc.chunk_ids = chunk_ids
        self.storage.add_document(doc)

        if self.use_graph:
            self._extract_entities_from_document(doc)

        return doc

    def add_text_content(self, text: str, title: str = "User Content") -> str:
        """Add text content directly."""
        doc_id = str(uuid.uuid4())
        doc = Document(
            id=doc_id,
            filename=title,
            content_type="text",
            text_content=text,
        )
        self.storage.add_document(doc)

        chunks = self.chunker.chunk_document(doc)
        chunk_ids = []

        for chunk in chunks:
            chunk_ids.append(chunk["id"])
            self.collection.upsert(
                ids=[chunk["id"]],
                documents=[chunk["text"]],
                embeddings=[self.embed(chunk["text"])],
                metadatas=[{
                    "title": f"{title} (chunk {chunk['chunk_index'] + 1}/{chunk['total_chunks']})",
                    "document_id": doc_id,
                    "chunk_index": chunk["chunk_index"],
                }],
            )

        doc.chunk_ids = chunk_ids
        self.storage.add_document(doc)

        if self.use_graph:
            self._extract_entities_from_document(doc)

        return doc_id

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its chunks."""
        doc = self.storage.get_document(doc_id)
        if not doc:
            return False

        for chunk_id in doc.chunk_ids:
            try:
                self.collection.delete(ids=[chunk_id])
            except Exception:
                pass

        self.storage.delete_document(doc_id)
        return True

    def retrieve(self, question: str) -> list[RetrievedSource]:
        """Retrieve relevant sources with feedback and graph adjustments."""
        if self.collection.count() == 0:
            raise RuntimeError("ChromaDB collection is empty. Run with --rebuild to recreate the index.")

        query_embedding = self.embed(question)
        n_results = min(self.top_k * 2, self.collection.count())

        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]

        feedback_scores = {}
        if self.use_feedback:
            feedback_scores = self.storage.get_source_feedback_scores()

        graph_boosts = {}
        if self.use_graph:
            graph_boosts = self._get_graph_boosts(question)

        sources: list[RetrievedSource] = []
        for i, doc_text in enumerate(documents):
            doc_id = ids[i] if i < len(ids) else f"unknown_{i}"
            metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            distance = distances[i] if i < len(distances) else None

            feedback_score = feedback_scores.get(doc_id, 0.0)
            graph_boost = graph_boosts.get(doc_id, 0.0)

            base_score = 1.0 / (1.0 + distance) if distance is not None else 0.5
            adjusted_score = (
                base_score
                + self.feedback_weight * feedback_score
                + self.graph_weight * graph_boost
            )

            sources.append(
                RetrievedSource(
                    id=doc_id,
                    title=metadata.get("title", "Untitled source"),
                    text=doc_text,
                    distance=distance,
                    feedback_score=feedback_score,
                    adjusted_score=adjusted_score,
                    graph_boost=graph_boost,
                )
            )

        sources.sort(key=lambda s: s.adjusted_score, reverse=True)
        return sources[:self.top_k]

    def _get_graph_boosts(self, question: str) -> dict[str, float]:
        """Calculate graph-based boosts for documents."""
        boosts: dict[str, float] = {}

        entities = self.storage.list_entities()
        matched_entities = []

        question_lower = question.lower()
        for entity in entities:
            if entity.name.lower() in question_lower:
                matched_entities.append(entity)

        for entity in matched_entities:
            for doc_id in entity.document_ids:
                boosts[doc_id] = boosts.get(doc_id, 0.0) + 1.0

            related = self.storage.get_related_entities(entity.id, max_depth=2)
            for related_entity, depth in related:
                boost_value = 0.5 / depth
                for doc_id in related_entity.document_ids:
                    boosts[doc_id] = boosts.get(doc_id, 0.0) + boost_value

        return boosts

    def _extract_entities_from_knowledge_base(self) -> None:
        """Extract entities from default knowledge base."""
        entity_definitions = [
            ("Raspberry Pi 5", "hardware", "Single-board computer for edge computing"),
            ("Ollama", "software", "Local LLM runtime"),
            ("ChromaDB", "software", "Vector database"),
            ("RAG", "concept", "Retrieval-Augmented Generation"),
            ("LLM", "concept", "Large Language Model"),
            ("embedding", "concept", "Vector representation of text"),
        ]

        entity_map = {}
        for name, etype, desc in entity_definitions:
            entity = Entity(
                id=str(uuid.uuid4()),
                name=name,
                entity_type=etype,
                description=desc,
                document_ids=[],
            )

            for item in KNOWLEDGE_BASE:
                if name.lower() in item["text"].lower():
                    entity.document_ids.append(item["id"])

            self.storage.add_entity(entity)
            entity_map[name] = entity

        relationships = [
            ("Raspberry Pi 5", "runs", "Ollama"),
            ("Ollama", "provides", "LLM"),
            ("Ollama", "provides", "embedding"),
            ("RAG", "uses", "ChromaDB"),
            ("RAG", "uses", "LLM"),
            ("RAG", "uses", "embedding"),
            ("ChromaDB", "stores", "embedding"),
        ]

        for source_name, rel_type, target_name in relationships:
            if source_name in entity_map and target_name in entity_map:
                rel = Relationship(
                    id=str(uuid.uuid4()),
                    source_entity_id=entity_map[source_name].id,
                    target_entity_id=entity_map[target_name].id,
                    relationship_type=rel_type,
                )
                self.storage.add_relationship(rel)

    def _extract_entities_from_document(self, doc: Document) -> None:
        """Extract entities from a document using simple pattern matching."""
        text = doc.text_content.lower()

        known_entities = self.storage.list_entities()
        for entity in known_entities:
            if entity.name.lower() in text:
                if doc.id not in entity.document_ids:
                    entity.document_ids.append(doc.id)
                    self.storage.add_entity(entity)

    def add_feedback(
        self,
        question: str,
        answer: str,
        rating: str,
        source_ids: list[str],
        comment: Optional[str] = None,
    ) -> str:
        """Add feedback for a Q&A interaction."""
        feedback = Feedback(
            id=str(uuid.uuid4()),
            question=question,
            answer=answer,
            rating=rating,
            comment=comment,
            source_ids=source_ids,
        )
        self.storage.add_feedback(feedback)
        return feedback.id

    def build_prompt(
        self,
        question: str,
        sources: list[RetrievedSource],
        graph_context: Optional[GraphContext] = None,
    ) -> str:
        """Build prompt with context."""
        context_parts = []
        for i, source in enumerate(sources, start=1):
            context_parts.append(f"[{i}] {source.title}\n{source.text}")

        context = "\n\n".join(context_parts)

        graph_info = ""
        if graph_context and (graph_context.entities or graph_context.relationships):
            graph_parts = []
            if graph_context.entities:
                entity_names = [e.name for e in graph_context.entities]
                graph_parts.append(f"相關概念: {', '.join(entity_names)}")
            if graph_context.relationships:
                rel_strs = [f"{s} {r} {t}" for s, r, t in graph_context.relationships]
                graph_parts.append(f"關係: {'; '.join(rel_strs)}")
            graph_info = "\n\n知識圖譜資訊:\n" + "\n".join(graph_parts)

        return textwrap.dedent(
            f"""
            你是一個在 Raspberry Pi 5 16GB 本機執行的 RAG AI 助手。
            請只根據下方 context 回答問題；如果 context 不足，請明確說「目前資料不足」。
            回答請使用繁體中文，並保持簡潔。

            context:
            {context}{graph_info}

            question:
            {question}

            answer:
            """
        ).strip()

    def get_graph_context(self, question: str) -> GraphContext:
        """Get graph context for a question."""
        context = GraphContext()

        entities = self.storage.list_entities()
        question_lower = question.lower()

        for entity in entities:
            if entity.name.lower() in question_lower:
                context.entities.append(entity)

                rels = self.storage.get_relationships_for_entity(entity.id)
                for rel in rels:
                    source_entity = self.storage.get_entity(rel.source_entity_id)
                    target_entity = self.storage.get_entity(rel.target_entity_id)
                    if source_entity and target_entity:
                        context.relationships.append(
                            (source_entity.name, rel.relationship_type, target_entity.name)
                        )

        return context

    def answer(self, question: str) -> tuple[str, list[RetrievedSource]]:
        """Generate answer for a question."""
        sources = self.retrieve(question)
        graph_context = self.get_graph_context(question) if self.use_graph else None
        prompt = self.build_prompt(question, sources, graph_context)
        response = self.ollama.generate(model=self.generation_model, prompt=prompt)
        return response["response"].strip(), sources

    def stream_answer(self, question: str) -> tuple[Iterator[str], list[RetrievedSource]]:
        """Stream answer generation."""
        sources = self.retrieve(question)
        graph_context = self.get_graph_context(question) if self.use_graph else None
        prompt = self.build_prompt(question, sources, graph_context)

        response_stream = self.ollama.generate(
            model=self.generation_model,
            prompt=prompt,
            stream=True,
        )

        def chunks() -> Iterator[str]:
            for chunk in response_stream:
                text = chunk.get("response", "")
                if text:
                    yield text

        return chunks(), sources

    def get_stats(self) -> dict:
        """Get RAG statistics."""
        storage_stats = self.storage.get_stats()
        return {
            "vector_db": {
                "collection": self.collection_name,
                "document_count": self.collection.count(),
            },
            "storage": storage_stats,
            "models": {
                "embed_model": self.embed_model,
                "generation_model": self.generation_model,
            },
            "settings": {
                "top_k": self.top_k,
                "use_feedback": self.use_feedback,
                "use_graph": self.use_graph,
            },
        }
