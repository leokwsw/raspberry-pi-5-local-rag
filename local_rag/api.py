import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from local_rag.config import Settings
from local_rag.database import Database
from local_rag.generation import (
    EchoGenerator,
    Generator,
    OllamaGenerator,
    OpenAICompatibleGenerator,
)
from local_rag.rag import RagService, parse_document
from local_rag.resources import JobQueue, system_metrics


class ChatRequest(BaseModel):
    question: str


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    config = settings or Settings()
    config.ensure_directories()
    database = Database(config.database_path)
    database.migrate()
    generator: Generator
    if not config.model_name:
        generator = EchoGenerator()
    elif config.llm_backend == "ollama":
        generator = OllamaGenerator(config.ollama_url, config.model_name)
    else:
        generator = OpenAICompatibleGenerator(config.llamacpp_url, config.model_name)
    rag = RagService(database, generator)
    jobs = JobQueue(database)
    jobs.recover()
    app = FastAPI(title="Pi Local RAG", version="0.1.0")
    app.state.rag = rag

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics")
    def metrics() -> dict[str, object]:
        return system_metrics(str(config.data_dir))

    @app.get("/jobs")
    def list_jobs() -> list[dict[str, object]]:
        return jobs.list()

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, object]:
        job = next((item for item in jobs.list() if item["id"] == job_id), None)
        if not job:
            raise HTTPException(404, detail={"code": "job_not_found"})
        return job

    @app.get("/documents")
    def documents() -> list[dict[str, object]]:
        return rag.documents()

    @app.post("/documents", status_code=201)
    async def upload(file: Annotated[UploadFile, File()]) -> dict[str, str]:
        suffix = Path(file.filename or "document.txt").suffix
        with tempfile.NamedTemporaryFile(suffix=suffix) as target:
            target.write(await file.read())
            target.flush()
            text = parse_document(Path(target.name), file.content_type or "text/plain")
        document_id = rag.ingest(
            file.filename or "document", file.content_type or "text/plain", text
        )
        return {"id": document_id}

    @app.delete("/documents/{document_id}", status_code=204)
    def delete(document_id: str) -> None:
        if not rag.delete(document_id):
            raise HTTPException(404, detail={"code": "document_not_found"})

    @app.post("/documents/{document_id}/ingest")
    def reindex(document_id: str) -> dict[str, str]:
        if not any(item["id"] == document_id for item in rag.documents()):
            raise HTTPException(404, detail={"code": "document_not_found"})
        return {"status": "already_indexed"}

    @app.post("/chat")
    async def chat(request: ChatRequest) -> StreamingResponse:
        async def events() -> AsyncIterator[str]:
            answer, evidence = await rag.answer(request.question)
            payload = {"answer": answer, "citations": [item.citation() for item in evidence]}
            yield f"data: {json.dumps(payload)}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return app


app = create_app()
