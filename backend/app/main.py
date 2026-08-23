import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .clients import ServiceError, chunk, embed, extract_triples, generate, rerank
from .config import get_settings
from .documents import DocumentRegistry
from .graph import KnowledgeGraphStore
from .memory import ConversationMemory
from .retrieval import bm25_search, needs_query_rewrite, reciprocal_rank_fusion
from .schemas import (Citation, ConversationMessage, ConversationResponse, DocumentList, DocumentSummary,
                      KnowledgeGraph, OllamaModel, ProcessRequest, QueryRequest, QueryResponse, SystemOverview, TripleItem)
from .store import VectorStore
from .text_files import decode_text

settings = get_settings()
logger = logging.getLogger(__name__)
store = VectorStore(settings.qdrant_url, settings.qdrant_collection)
memory = ConversationMemory(settings.memory_db_path, settings.memory_max_messages)
graph_store = KnowledgeGraphStore(
    settings.arangodb_url,
    settings.arangodb_database,
    settings.arangodb_username,
    settings.arangodb_password,
)
documents = DocumentRegistry(settings.document_db_path, settings.upload_dir)


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


async def is_healthy(url: str, auth: tuple[str, str] | None = None) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            return (await client.get(url, auth=auth)).is_success
    except httpx.HTTPError:
        return False


@app.get("/api/health")
async def health():
    ollama, qdrant, arangodb, reranker, chunker = await asyncio.gather(
        is_healthy(f"{settings.ollama_base_url.rstrip('/')}/api/tags"),
        is_healthy(f"{settings.qdrant_url.rstrip('/')}/healthz"),
        is_healthy(f"{settings.arangodb_url.rstrip('/')}/_api/version",
                   (settings.arangodb_username, settings.arangodb_password)),
        is_healthy(f"{settings.reranker_url.rstrip('/')}/health"),
        is_healthy(f"{settings.chunking_url.rstrip('/')}/health"),
    )
    return {"status": "ok" if all((ollama, qdrant, arangodb, reranker, chunker)) else "degraded",
            "services": {"ollama": ollama, "qdrant": qdrant, "arangodb": arangodb,
                         "reranker": reranker, "chunking": chunker}}


async def vector_store_overview() -> dict:
    try:
        return await store.overview()
    except Exception as exc:  # Qdrant client exposes several transport-specific exception types.
        logger.warning("Unable to read Qdrant overview: %s", exc)
        return {"connected": False, "vector_count": 0}


@app.get("/api/overview", response_model=SystemOverview)
async def system_overview():
    document_list, graph, arangodb_connected, vector_overview = await asyncio.gather(
        list_documents(),
        asyncio.to_thread(graph_store.graph),
        is_healthy(f"{settings.arangodb_url.rstrip('/')}/_api/version",
                   (settings.arangodb_username, settings.arangodb_password)),
        vector_store_overview(),
    )
    return SystemOverview(
        chat_model=settings.ollama_chat_model,
        embedding_model=settings.ollama_embed_model,
        documents_ready=sum(not (item.embeddings_ready and item.triples_ready)
                            for item in document_list.documents),
        arangodb_connected=arangodb_connected,
        arangodb_url=settings.arangodb_url,
        arangodb_database=settings.arangodb_database,
        graph_nodes=len(graph["nodes"]),
        graph_relationships=len(graph["edges"]),
        qdrant_connected=bool(vector_overview["connected"]),
        qdrant_url=settings.qdrant_url,
        qdrant_collection=settings.qdrant_collection,
        vector_count=int(vector_overview["vector_count"]),
    )


async def installed_ollama_models() -> list[dict]:
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
    return [{"name": str(item.get("name", "")), "size": int(item.get("size", 0))}
            for item in models if item.get("name")]


@app.get("/api/models", response_model=list[OllamaModel])
async def ollama_models():
    try:
        return [OllamaModel(**item) for item in await installed_ollama_models()]
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "無法取得 Ollama 模型清單") from exc


@app.post("/api/documents", response_model=DocumentSummary, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"檔案不可超過 {settings.max_upload_mb} MB")
    filename = file.filename or "unnamed.txt"
    decode_text(filename, content)
    document_id = str(uuid4())
    item = await asyncio.to_thread(documents.add, document_id, filename, content)
    return DocumentSummary(**item)


@app.get("/api/documents", response_model=DocumentList)
async def list_documents():
    graph_counts = await asyncio.to_thread(graph_store.document_counts)
    staged = await asyncio.to_thread(documents.list)
    staged_ids = {item["document_id"] for item in staged}
    legacy = [{**item, "embeddings_ready": True, "triples_ready": graph_counts.get(item["document_id"], 0) > 0,
               "graph_stored": graph_counts.get(item["document_id"], 0) > 0,
               "graph_triple_count": graph_counts.get(item["document_id"], 0)}
              for item in await store.list_documents() if item["document_id"] not in staged_ids]
    items = [DocumentSummary(**item) for item in [*staged, *legacy]]
    return DocumentList(documents=items, total_chunks=sum(item.chunk_count for item in items))


async def document_chunks(document_id: str, chunk_size: int | None = None,
                          chunk_overlap: int | None = None) -> tuple[dict, list[dict]]:
    try:
        item = await asyncio.to_thread(documents.get, document_id)
    except KeyError as exc:
        raise HTTPException(404, "找不到原始文件；舊版已處理文件不可重新處理") from exc
    chunks = item["chunks"]
    if not chunks or chunk_size is not None or chunk_overlap is not None:
        content = await asyncio.to_thread(Path(item["path"]).read_bytes)
        chunks = await chunk(settings.chunking_url, decode_text(item["filename"], content), chunk_size, chunk_overlap)
        await asyncio.to_thread(documents.update_chunks, document_id, chunks)
    return item, chunks


@app.post("/api/documents/process", response_model=DocumentList)
async def process_documents(request: ProcessRequest):
    chat_model = settings.ollama_chat_model
    if request.mode == "triples" and request.chat_model:
        try:
            installed_names = {item["name"] for item in await installed_ollama_models()}
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, "無法驗證 Ollama 模型") from exc
        if request.chat_model not in installed_names:
            raise HTTPException(400, "所選 Ollama 模型未安裝")
        chat_model = request.chat_model
    for document_id in request.document_ids:
        item, chunks = await document_chunks(document_id, request.chunk_size, request.chunk_overlap)
        if request.mode == "embeddings":
            vectors: list[list[float]] = []
            for start in range(0, len(chunks), 16):
                vectors.extend(await embed(settings.ollama_base_url, settings.ollama_embed_model,
                                           [chunk_item["text"] for chunk_item in chunks[start:start + 16]]))
            await store.delete_document(document_id)
            await store.add_document(document_id, item["filename"], item["size"], chunks, vectors)
            await asyncio.to_thread(documents.update_processing, document_id, embeddings_ready=True)
        else:
            triples: list[dict] = []
            batch_size = request.batch_chunks or max(1, settings.graph_batch_chunks)
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start:start + batch_size]
                triples.extend(await extract_triples(
                    settings.ollama_base_url, chat_model,
                    "\n\n".join(str(chunk_item["text"]) for chunk_item in batch), int(batch[0]["index"]),
                    request.system_prompt,
                ))
            await asyncio.to_thread(documents.update_processing, document_id, triples=triples)
    return await list_documents()


@app.get("/api/documents/{document_id}/download")
async def download_document(document_id: str):
    try:
        item = await asyncio.to_thread(documents.get, document_id)
    except KeyError as exc:
        raise HTTPException(404, "這是舊版索引，沒有保留可下載的原始檔") from exc
    return FileResponse(item["path"], filename=item["filename"], media_type="application/octet-stream")


@app.get("/api/triples", response_model=list[TripleItem])
async def list_triples():
    items: list[TripleItem] = []
    staged_documents = await asyncio.to_thread(documents.list)
    staged_ids = {document["document_id"] for document in staged_documents}
    for document in staged_documents:
        for index, triple in enumerate(document["triples"]):
            items.append(TripleItem(
                id=f'{document["document_id"]}-{index}', document_id=document["document_id"],
                filename=document["filename"], subject=str(triple["subject"]), predicate=str(triple["predicate"]),
                object=str(triple["object"]), chunk_index=int(triple.get("chunk_index", 0)),
                stored=document["graph_stored"],
            ))
    graph = await asyncio.to_thread(graph_store.graph)
    labels = {node["id"]: node["label"] for node in graph["nodes"]}
    items.extend(TripleItem(
        id=edge["id"], document_id=edge["document_id"], filename=edge["filename"],
        subject=labels.get(edge["source"], edge["source"]), predicate=edge["predicate"],
        object=labels.get(edge["target"], edge["target"]), chunk_index=edge["chunk_index"], stored=True,
    ) for edge in graph["edges"] if edge["document_id"] not in staged_ids)
    return items


@app.post("/api/triples/store")
async def store_triples():
    stored = 0
    for document in await asyncio.to_thread(documents.list):
        if document["triples_ready"] and not document["graph_stored"]:
            stored += await asyncio.to_thread(graph_store.replace_document, document["document_id"],
                                               document["filename"], document["triples"])
            await asyncio.to_thread(documents.mark_graph_stored, document["document_id"])
    return {"stored": stored}


@app.delete("/api/documents/{document_id}", status_code=204)
async def delete_document(document_id: str):
    await asyncio.gather(
        store.delete_document(document_id),
        asyncio.to_thread(graph_store.delete_document, document_id),
        asyncio.to_thread(documents.delete, document_id),
    )


@app.get("/api/graph", response_model=KnowledgeGraph)
async def knowledge_graph(document_id: str | None = None):
    return await asyncio.to_thread(graph_store.graph, document_id)


@app.get("/api/conversations/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str):
    messages = await asyncio.to_thread(memory.recent, session_id)
    return ConversationResponse(session_id=session_id, messages=[ConversationMessage(**item) for item in messages])


@app.delete("/api/conversations/{session_id}", status_code=204)
async def clear_conversation(session_id: str):
    await asyncio.to_thread(memory.clear, session_id)


async def rewrite_question(question: str, history: list[dict], chat_model: str) -> str:
    if not needs_query_rewrite(question, bool(history)):
        return question
    transcript = "\n".join(f"{item['role']}: {item['content']}" for item in history[-4:])
    rewritten = await generate(settings.ollama_base_url, chat_model, [
        {"role": "system", "content": "把追問改寫成可獨立檢索的問題。只輸出改寫後問題，不回答。"},
        {"role": "user", "content": f"對話：\n{transcript}\n\n追問：{question}\n\n/no_think"},
    ])
    return rewritten.strip() or question


async def build_context(citations: list[Citation], lookup: dict[str, dict], ranked: list[dict]) -> str:
    neighbor_groups = await asyncio.gather(*[
        store.neighbors(
            str(lookup[item["id"]]["document_id"]),
            int(lookup[item["id"]]["chunk_index"]),
            settings.neighbor_window,
        )
        for item in ranked if item["id"] in lookup
    ])
    sections: list[str] = []
    for citation, neighbors in zip(citations, neighbor_groups, strict=True):
        unique_texts = list(dict.fromkeys(str(item.get("text", "")) for item in neighbors if item.get("text")))
        text = "\n\n".join(unique_texts) or citation.text
        sections.append(f"[{citation.index}] {citation.filename}（命中區塊 {citation.chunk_index}，含相鄰內容）\n{text}")
    return "\n\n".join(sections)


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    chat_model = settings.ollama_chat_model
    if request.chat_model:
        try:
            installed_names = {item["name"] for item in await installed_ollama_models()}
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, "無法驗證 Ollama 模型") from exc
        if request.chat_model not in installed_names:
            raise HTTPException(400, "所選 Ollama 模型未安裝")
        chat_model = request.chat_model
    session_id = request.session_id or memory.new_session_id()
    history = await asyncio.to_thread(memory.recent, session_id)
    retrieval_query = await rewrite_question(request.question, history, chat_model)
    vector = (await embed(settings.ollama_base_url, settings.ollama_embed_model, [retrieval_query]))[0]
    multiplier = {"quick": 0.5, "standard": 1.0, "deep": 1.5}[request.depth]
    candidate_limit = max(5, int(settings.retrieval_limit * multiplier))
    dense_candidates, all_chunks = await asyncio.gather(
        store.search(vector, candidate_limit, request.document_ids),
        store.all_chunks(request.document_ids),
    )
    lexical_candidates = bm25_search(retrieval_query, all_chunks, candidate_limit)
    candidates = reciprocal_rank_fusion([dense_candidates, lexical_candidates], candidate_limit)
    if not candidates:
        answer = "知識庫目前沒有可供查詢的內容，請先加入純文字文件。"
        await asyncio.to_thread(memory.append_exchange, session_id, request.question, answer)
        return QueryResponse(answer=answer, citations=[], session_id=session_id, rewritten_query=retrieval_query)
    ranked = await rerank(
        settings.reranker_url,
        retrieval_query,
        [{"id": item["id"], "text": item["text"]} for item in candidates],
        max(2, int(settings.rerank_limit * multiplier)),
    )
    lookup = {item["id"]: item for item in candidates}
    ranked = [item for item in ranked if item["id"] in lookup]
    if not ranked or float(ranked[0]["score"]) < settings.rerank_score_threshold:
        answer = "文件中沒有足夠可靠的資料可以回答這個問題。"
        await asyncio.to_thread(memory.append_exchange, session_id, request.question, answer)
        return QueryResponse(answer=answer, citations=[], session_id=session_id, rewritten_query=retrieval_query)
    citations = [
        Citation(index=index, filename=lookup[item["id"]]["filename"],
                 chunk_index=int(lookup[item["id"]]["chunk_index"]), score=float(item["score"]), text=item["text"])
        for index, item in enumerate(ranked, start=1)
    ]
    context = await build_context(citations, lookup, ranked)
    if request.search_mode == "graph":
        graph = await asyncio.to_thread(graph_store.graph)
        terms = {term.casefold() for term in retrieval_query.split() if len(term) > 1}
        labels = {node["id"]: node["label"] for node in graph["nodes"]}
        matching_edges = [edge for edge in graph["edges"] if any(
            term in f'{labels.get(edge["source"], "")} {edge["predicate"]} {labels.get(edge["target"], "")}'.casefold()
            for term in terms
        )][:20]
        if matching_edges:
            graph_context = "\n".join(
                f'- {labels.get(edge["source"], edge["source"])} — {edge["predicate"]} → '
                f'{labels.get(edge["target"], edge["target"])}' for edge in matching_edges
            )
            context = f"{context}\n\n知識圖譜關係：\n{graph_context}"
    language_rule = "請一律使用繁體中文回答。" if request.language == "zh-Hant" else "請跟隨使用者問題的語言回答。"
    messages = [
        {"role": "system",
         "content": f"你是嚴謹的本機知識庫助手。{language_rule}只可根據本次提供的文件內容回答；不足時直接說明。引用事實時使用 [1] 格式標記來源。對話歷史只用於理解追問，不可當作事實來源。不要顯示思考過程。"},
        *history[-6:],
        {"role": "user", "content": f"問題：{request.question}\n\n可用內容：\n{context}\n\n/no_think"},
    ]
    answer = await generate(settings.ollama_base_url, chat_model, messages)
    answer = answer or "模型沒有產生答案。"
    await asyncio.to_thread(memory.append_exchange, session_id, request.question, answer)
    return QueryResponse(answer=answer, citations=citations, session_id=session_id,
                         rewritten_query=retrieval_query if retrieval_query != request.question else None)
