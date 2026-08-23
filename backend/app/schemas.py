from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    language: Literal["zh-Hant", "follow"] = "zh-Hant"
    depth: Literal["quick", "standard", "deep"] = "standard"
    session_id: str | None = Field(default=None, min_length=1, max_length=64)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    search_mode: Literal["pure", "graph"] = "pure"
    chat_model: str | None = Field(default=None, min_length=1, max_length=200)


class Citation(BaseModel):
    index: int
    filename: str
    chunk_index: int
    score: float
    text: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    session_id: str
    rewritten_query: str | None = None


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ConversationResponse(BaseModel):
    session_id: str
    messages: list[ConversationMessage]


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    size: int
    chunk_count: int
    graph_triple_count: int = 0
    embeddings_ready: bool = False
    triples_ready: bool = False
    graph_stored: bool = False


class ProcessRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1, max_length=50)
    mode: Literal["embeddings", "triples"]
    system_prompt: str | None = Field(default=None, min_length=20, max_length=12000)
    chunk_size: int | None = Field(default=None, ge=200, le=4000)
    chunk_overlap: int | None = Field(default=None, ge=0, le=1000)
    batch_chunks: int | None = Field(default=None, ge=1, le=16)
    chat_model: str | None = Field(default=None, min_length=1, max_length=200)


class OllamaModel(BaseModel):
    name: str
    size: int = 0


class TripleItem(BaseModel):
    id: str
    subject: str
    predicate: str
    object: str
    document_id: str
    filename: str
    chunk_index: int
    stored: bool


class DocumentList(BaseModel):
    documents: list[DocumentSummary]
    total_chunks: int


class GraphNode(BaseModel):
    id: str
    label: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    predicate: str
    document_id: str
    filename: str
    chunk_index: int


class KnowledgeGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SystemOverview(BaseModel):
    chat_model: str
    embedding_model: str
    documents_ready: int
    arangodb_connected: bool
    arangodb_url: str
    arangodb_database: str
    graph_nodes: int
    graph_relationships: int
    qdrant_connected: bool
    qdrant_url: str
    qdrant_collection: str
    vector_count: int
