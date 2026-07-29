# Raspberry Pi 5 Local RAG

A self-contained, CPU-first Text RAG, Knowledge Graph and GraphRAG appliance for Raspberry Pi 5.
Cloud LLM and embedding APIs are not required.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[pdf,test]'
.venv/bin/uvicorn local_rag.api:app --reload
```

Run quality gates with:

```bash
.venv/bin/ruff check .
.venv/bin/mypy local_rag
.venv/bin/pytest
cd apps/web && npm install && npm run build
```

The API exposes documents, SSE chat, jobs, metrics, graph search and voice capabilities.
Hardware benchmark outputs remain `pending-device-validation` until executed on the target Pi.
