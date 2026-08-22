from typing import List

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"

app = FastAPI(
    title="Reranker Service",
    version="1.0.0"
)

model = CrossEncoder(
    MODEL_NAME,
    max_length=1024
)

model.tokenizer.pad_token = model.tokenizer.eos_token


class Document(BaseModel):
    id: str
    text: str


class RerankRequest(BaseModel):
    query: str
    documents: List[Document]
    top_n: int = 5


class RerankResult(BaseModel):
    id: str
    text: str
    score: float
    rank: int


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": MODEL_NAME
    }


@app.post("/rerank")
def rerank(request: RerankRequest):
    if not request.documents:
        return {
            "results": []
        }

    pairs = [
        (request.query, doc.text)
        for doc in request.documents
    ]

    scores = model.predict(
        pairs,
        activation_fn=torch.nn.Sigmoid()
    )

    results = []

    for doc, score in zip(request.documents, scores):
        results.append({
            "id": doc.id,
            "text": doc.text,
            "score": float(score)
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    results = results[:request.top_n]

    for index, result in enumerate(results):
        result["rank"] = index + 1

    return {
        "query": request.query,
        "results": results
    }
