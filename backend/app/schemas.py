from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    language: Literal["zh-Hant", "follow"] = "zh-Hant"
    depth: Literal["quick", "standard", "deep"] = "standard"
    session_id: str | None = Field(default=None, min_length=1, max_length=64)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    search_mode: Literal["pure", "graph"] = "pure"


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
