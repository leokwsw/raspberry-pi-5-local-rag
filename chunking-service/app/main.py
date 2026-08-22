import os
import re

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Plain Text Chunking Service", version="1.0.0")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))


class ChunkRequest(BaseModel):
    text: str = Field(min_length=1)
    chunk_size: int | None = Field(default=None, ge=200, le=4000)
    overlap: int | None = Field(default=None, ge=0, le=1000)


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            windows = [
                paragraph[start:start + chunk_size]
                for start in range(0, len(paragraph), max(1, chunk_size - overlap))
            ]
            chunks.extend(windows[:-1])
            current = windows[-1]
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{paragraph}".strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chunk")
def chunk(request: ChunkRequest):
    chunk_size = request.chunk_size or CHUNK_SIZE
    overlap = min(request.overlap if request.overlap is not None else CHUNK_OVERLAP, chunk_size // 2)
    chunks = split_text(request.text, chunk_size, overlap)
    return {"chunks": [{"index": index, "text": text, "characters": len(text)} for index, text in enumerate(chunks)]}
