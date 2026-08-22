from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    language: Literal["zh-Hant", "follow"] = "zh-Hant"
    depth: Literal["quick", "standard", "deep"] = "standard"


class Citation(BaseModel):
    index: int
    filename: str
    chunk_index: int
    score: float
    text: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    size: int
    chunk_count: int


class DocumentList(BaseModel):
    documents: list[DocumentSummary]
    total_chunks: int
