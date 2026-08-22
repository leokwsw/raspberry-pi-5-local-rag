import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .clients import ServiceError, chunk, embed, generate, rerank
from .config import get_settings
from .schemas import Citation, DocumentList, DocumentSummary, QueryRequest, QueryResponse
from .store import VectorStore
from .text_files import decode_text

settings = get_settings()
store = VectorStore(settings.qdrant_url, settings.qdrant_collection)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await store.client.close()


app = FastAPI(title="Raspberry Pi Local RAG", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(ServiceError)
async def service_error_handler(_, exc: ServiceError):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def is_healthy(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            return (await client.get(url)).is_success
    except httpx.HTTPError:
        return False


@app.get("/api/health")
async def health():
    ollama, qdrant, reranker, chunker = await asyncio.gather(
        is_healthy(f"{settings.ollama_base_url.rstrip('/')}/api/tags"),
        is_healthy(f"{settings.qdrant_url.rstrip('/')}/healthz"),
        is_healthy(f"{settings.reranker_url.rstrip('/')}/health"),
        is_healthy(f"{settings.chunking_url.rstrip('/')}/health"),
    )
    return {"status": "ok" if all((ollama, qdrant, reranker, chunker)) else "degraded",
            "services": {"ollama": ollama, "qdrant": qdrant, "reranker": reranker, "chunking": chunker}}


@app.post("/api/documents", response_model=DocumentSummary, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"檔案不可超過 {settings.max_upload_mb} MB")
    filename = file.filename or "unnamed.txt"
    text = decode_text(filename, content)
    chunks = await chunk(settings.chunking_url, text)
    vectors: list[list[float]] = []
    for start in range(0, len(chunks), 16):
        vectors.extend(await embed(settings.ollama_base_url, settings.ollama_embed_model,
                                   [item["text"] for item in chunks[start:start + 16]]))
    document_id = str(uuid4())
    await store.add_document(document_id, filename, len(content), chunks, vectors)
    return DocumentSummary(document_id=document_id, filename=filename, size=len(content), chunk_count=len(chunks))


@app.get("/api/documents", response_model=DocumentList)
async def list_documents():
    documents = [DocumentSummary(**item) for item in await store.list_documents()]
    return DocumentList(documents=documents, total_chunks=sum(item.chunk_count for item in documents))


@app.delete("/api/documents/{document_id}", status_code=204)
async def delete_document(document_id: str):
    await store.delete_document(document_id)


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    vector = (await embed(settings.ollama_base_url, settings.ollama_embed_model, [request.question]))[0]
    multiplier = {"quick": 0.5, "standard": 1.0, "deep": 1.5}[request.depth]
    candidates = await store.search(vector, max(5, int(settings.retrieval_limit * multiplier)))
    if not candidates:
        return QueryResponse(answer="知識庫目前沒有可供查詢的內容，請先加入純文字文件。", citations=[])
    ranked = await rerank(
        settings.reranker_url,
        request.question,
        [{"id": item["id"], "text": item["text"]} for item in candidates],
        max(2, int(settings.rerank_limit * multiplier)),
    )
    lookup = {item["id"]: item for item in candidates}
    citations = [
        Citation(index=index, filename=lookup[item["id"]]["filename"],
                 chunk_index=int(lookup[item["id"]]["chunk_index"]), score=float(item["score"]), text=item["text"])
        for index, item in enumerate(ranked, start=1) if item["id"] in lookup
    ]
    context = "\n\n".join(f"[{item.index}] {item.filename}（區塊 {item.chunk_index}）\n{item.text}" for item in citations)
    language_rule = "請一律使用繁體中文回答。" if request.language == "zh-Hant" else "請跟隨使用者問題的語言回答。"
    messages = [
        {"role": "system",
         "content": f"你是嚴謹的本機知識庫助手。{language_rule}只可根據提供的內容回答；不足時直接說明。引用事實時使用 [1] 格式標記來源。不要顯示思考過程。"},
        {"role": "user", "content": f"問題：{request.question}\n\n可用內容：\n{context}\n\n/no_think"},
    ]
    answer = await generate(settings.ollama_base_url, settings.ollama_chat_model, messages)
    return QueryResponse(answer=answer or "模型沒有產生答案。", citations=citations)
