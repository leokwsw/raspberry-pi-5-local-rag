# Raspberry Pi 5 Local RAG / Knowledge Graph RAG — Project Plan

## 1. Project Goal

Build a **fully self-contained Local RAG / Knowledge Graph RAG appliance** that runs entirely on a single:

- Raspberry Pi 5
- 16 GB RAM
- ARM64 Linux
- No external GPU
- No cloud LLM API
- No cloud embedding API
- No second machine for inference

The system must eventually provide:

```text
Document
  -> Parse
  -> Chunk
  -> Embed
  -> Index
  -> Retrieve
  -> Build Context
  -> Local LLM
  -> Answer
```

Then progressively extend into:

```text
Document
  -> Parse
  -> Chunk
  -> Knowledge Extraction
  -> Subject-Predicate-Object Triples
  -> Knowledge Graph
```

and finally:

```text
Question
  -> Dense Retrieval
  +  BM25 / Keyword Retrieval
  +  Knowledge Graph Retrieval
  -> Rank / Merge
  -> Context Construction
  -> Local LLM
  -> Answer
```

The project is not only intended to prove that a Raspberry Pi can run RAG.

The research question is:

> **How far can a Raspberry Pi 5 16 GB be pushed as a fully self-contained RAG / GraphRAG knowledge appliance?**

---

## 2. Reference Projects

The project should use the following repositories as architectural references:

### NVIDIA txt2kg Playbook

https://github.com/NVIDIA/dgx-spark-playbooks/tree/main/nvidia/txt2kg/assets

Reference concepts:

- Document ingestion
- Text parsing
- Chunking
- Embedding
- Vector retrieval
- LLM-based knowledge extraction
- Subject-Predicate-Object triples
- Graph database
- RAG / graph-assisted retrieval
- API / frontend separation
- Docker Compose based service orchestration

### Derived txt2kg Repository

https://github.com/leokwsw/dgx-spark-txt2kg

This repository can be used as a more implementation-oriented reference for:

- Project structure
- Service boundaries
- Data flow
- Prompts
- Knowledge extraction
- API patterns
- Graph visualization

However, the Raspberry Pi version must **not** copy the DGX Spark architecture directly.

The following assumptions must be removed or replaced:

- CUDA
- NVIDIA Container Toolkit
- vLLM
- GPU-only acceleration
- DGX Spark / GB300 assumptions
- Large LLMs
- GPU-sized embedding models
- Heavy multi-service architecture
- Memory-heavy graph/vector services where lighter alternatives exist

---

# 3. Design Principles

## 3.1 Raspberry Pi First

Every technical decision must be evaluated against:

- RAM usage
- CPU usage
- Memory bandwidth
- ARM64 compatibility
- Storage I/O
- Model load time
- Thermal behaviour
- Long-running stability
- Concurrent workload impact

A component is not accepted simply because it can technically run.

It must demonstrate acceptable cost versus benefit on Raspberry Pi 5.

---

## 3.2 Build in Layers

Development order:

```text
Text RAG
    ↓
Hybrid RAG
    ↓
Knowledge Extraction
    ↓
Knowledge Graph
    ↓
Graph-assisted RAG
    ↓
GraphRAG
    ↓
Voice
```

Do not build all subsystems simultaneously.

Each phase must have measurable exit criteria before the next phase begins.

---

## 3.3 Minimize Idle Resource Cost

Avoid architectures where multiple heavy services remain resident in memory without actively contributing to a query.

Prefer:

- SQLite
- in-process libraries
- local files
- lightweight APIs
- single-worker execution
- model reuse
- explicit load/unload policies

before introducing:

- multiple database servers
- JVM services
- distributed components
- orchestration infrastructure

---

# 4. Target Architecture

## 4.1 Phase 1 Architecture — Text RAG

```text
                         ┌─────────────────────┐
                         │      Web UI         │
                         │   Browser Client    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      Backend API    │
                         │ FastAPI / equivalent│
                         └───────┬───────┬─────┘
                                 │       │
                    Query        │       │ Upload
                                 │       │
                                 ▼       ▼
                      ┌──────────────┐  ┌──────────────┐
                      │ Query Engine │  │ Ingestion API│
                      └──────┬───────┘  └──────┬───────┘
                             │                 │
                             │          ┌──────▼───────┐
                             │          │ Job Queue    │
                             │          │ single worker│
                             │          └──────┬───────┘
                             │                 │
                             │          Parse -> Chunk
                             │                 │
                             │                 ▼
                             │           Embedding Model
                             │                 │
                             │                 ▼
                             │            Vector Index
                             │
                             ▼
                 Dense + BM25 Retrieval
                             │
                             ▼
                   Context Construction
                             │
                             ▼
                      Local LLM Runtime
                             │
                             ▼
                           Answer
```

---

## 4.2 Final Target Architecture

```text
                         Browser
                            │
                            ▼
                     Lightweight UI
                            │
                            ▼
                       Backend API
                  ┌─────────┴─────────┐
                  │                   │
             Query Pipeline      Ingestion Pipeline
                  │                   │
                  │            Parse / Normalize
                  │                   │
                  │                 Chunk
                  │              ┌────┴────┐
                  │              │         │
                  │           Embed   KG Extraction
                  │              │         │
                  │              ▼         ▼
                  │          Vector DB   Graph Store
                  │              │         │
                  └──────┬───────┴────┬────┘
                         │            │
                    BM25 Search   Graph Retrieval
                         │            │
                         └─────┬──────┘
                               ▼
                         Fusion / Rerank
                               │
                               ▼
                      Context Construction
                               │
                               ▼
                          Local LLM
                               │
                               ▼
                             Answer
```

---

# 5. Proposed Technology Stack

The stack is intentionally provisional.

Final selection must be based on Raspberry Pi benchmarks.

| Layer | Initial Choice | Alternatives |
|---|---|---|
| OS | Raspberry Pi OS 64-bit / Debian ARM64 | Ubuntu Server ARM64 |
| LLM Runtime | llama.cpp | Ollama |
| LLM Format | GGUF | — |
| Quantization | Q4_K_M baseline | Q5_K_M |
| Backend | Python + FastAPI | Go / Rust for selected services |
| Parsing | PyMuPDF + plain text parsers | pypdf / Docling if viable |
| Chunking | Native Python implementation | semantic chunking later |
| Embedding | lightweight multilingual model | ONNX / llama.cpp embedding |
| Metadata | SQLite | PostgreSQL not planned initially |
| BM25 | SQLite FTS5 | Tantivy-based solution |
| Dense Vector | sqlite-vec baseline | FAISS / Qdrant / LanceDB |
| Graph | SQLite tables baseline | ArangoDB later comparison |
| Frontend | lightweight React / Next.js static client | plain React / Vue |
| API | REST initially | WebSocket/SSE for streaming |
| Process Control | systemd | Docker Compose |
| Benchmark | Python scripts + psutil | perf / hyperfine / vcgencmd |

---

# 6. Repository Structure

Proposed repository layout:

```text
raspberry-pi-local-rag/
│
├── README.md
├── PLAN.md
├── LICENSE
├── .env.example
├── pyproject.toml
│
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   └── services/
│   │
│   └── web/
│       ├── src/
│       └── package.json
│
├── core/
│   ├── config/
│   ├── parsing/
│   ├── chunking/
│   ├── embeddings/
│   ├── retrieval/
│   │   ├── bm25/
│   │   ├── dense/
│   │   ├── hybrid/
│   │   └── graph/
│   ├── generation/
│   ├── prompts/
│   ├── reranking/
│   └── graph/
│
├── workers/
│   ├── ingestion/
│   ├── knowledge_extraction/
│   └── queue/
│
├── storage/
│   ├── metadata/
│   ├── vector/
│   └── graph/
│
├── models/
│   ├── llm/
│   └── embeddings/
│
├── benchmark/
│   ├── datasets/
│   ├── llm/
│   ├── embedding/
│   ├── retrieval/
│   ├── storage/
│   ├── thermal/
│   ├── end_to_end/
│   └── results/
│
├── scripts/
│   ├── setup_pi.sh
│   ├── download_models.sh
│   ├── benchmark.sh
│   └── backup.sh
│
├── deploy/
│   ├── systemd/
│   ├── docker/
│   └── config/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── retrieval/
│
└── docs/
    ├── architecture.md
    ├── benchmark-methodology.md
    ├── model-selection.md
    ├── storage-comparison.md
    ├── graph-design.md
    └── decisions/
```

Use Architecture Decision Records under:

```text
docs/decisions/
```

for major choices such as:

- llama.cpp vs Ollama
- sqlite-vec vs Qdrant
- embedding model selection
- graph storage selection
- Docker vs native systemd deployment

---

# 7. LLM Strategy

## 7.1 Runtime

First implementation:

```text
llama.cpp
```

Reasons:

- Native ARM64 support
- Low overhead
- Direct GGUF support
- Fine control over threads and context
- Easier benchmarking
- Minimal service stack

Ollama should be benchmarked separately for operational convenience.

LM Studio should not be considered the primary Raspberry Pi deployment runtime unless ARM64 server support and resource behaviour justify it.

---

## 7.2 Model Classes

Primary production candidates:

```text
1B
2B
3B
4B
```

Quantization:

```text
Q4_K_M
Q5_K_M
```

7B / 8B models should only be used as comparison points.

They should not be assumed to be production candidates merely because they fit into RAM.

---

## 7.3 LLM Benchmark Metrics

For each model:

- model file size
- model load time
- idle RAM
- peak RAM
- TTFT
- tokens/sec
- prompt processing tokens/sec
- CPU utilization
- temperature
- thermal throttling
- power consumption if measurable
- context length impact
- 1k / 2k / 4k / 8k context tests
- answer quality

Benchmark matrix example:

```text
Model × Quantization × Context Length × Thread Count
```

---

# 8. Embedding Strategy

Embedding must be completely local.

Primary requirements:

- ARM64 compatible
- CPU efficient
- multilingual
- English
- Traditional Chinese
- small memory footprint
- acceptable retrieval quality

Candidate families to benchmark may include lightweight multilingual sentence-transformer / BGE / E5-class models where ARM inference is practical.

Possible runtimes:

```text
PyTorch
ONNX Runtime
llama.cpp embedding mode
```

Do not lock the project to SentenceTransformers before benchmark results.

---

## 8.1 Embedding Metrics

Measure:

- model load time
- embedding latency
- chunks/sec
- documents/min
- average CPU
- peak CPU
- idle RAM
- peak RAM
- output dimension
- storage per 10k vectors
- retrieval Recall@K
- MRR / nDCG where appropriate
- Traditional Chinese retrieval quality
- English retrieval quality

---

# 9. Retrieval Strategy

The project should establish retrieval baselines before adding Knowledge Graph retrieval.

## Stage A

```text
BM25
```

SQLite FTS5 baseline.

## Stage B

```text
Dense Vector Search
```

Start with sqlite-vec or equivalent lightweight implementation.

## Stage C

```text
BM25 + Dense
```

Initial fusion:

```text
Reciprocal Rank Fusion
```

Later compare:

- weighted score fusion
- normalized score fusion
- reranking

## Stage D

```text
Hybrid + Graph
```

Only after KG retrieval has demonstrated measurable value.

---

# 10. Vector Storage Evaluation

Compare:

## SQLite + sqlite-vec

Expected strengths:

- minimal infrastructure
- same database for metadata + FTS + vectors
- low idle RAM
- simple backup
- ideal first implementation

## FAISS

Evaluate:

- in-process performance
- memory usage
- persistence
- metadata complexity

## Qdrant

Evaluate:

- ARM64 image availability
- service RAM
- indexing cost
- filtering
- operational overhead

## LanceDB

Evaluate:

- ARM support
- indexing
- metadata integration
- disk behaviour
- memory behaviour

Decision must be benchmark driven.

---

# 11. Knowledge Graph Strategy

Knowledge Graph is not a Phase 1 dependency.

First implementation should test whether useful triples can be extracted reliably using a Pi-sized model.

Pipeline:

```text
Chunk
  -> Extraction Prompt
  -> Local LLM
  -> Structured Output
  -> Validate
  -> Normalize Entities
  -> Store Triple
```

Triple:

```text
Subject
Predicate
Object
```

Additional fields:

```text
document_id
chunk_id
confidence
source_text
created_at
```

---

## 11.1 Graph Storage Baseline

Start with SQLite:

```text
nodes
edges
aliases
documents
chunks
```

Example:

```text
nodes(
    id,
    canonical_name,
    entity_type
)

edges(
    id,
    subject_id,
    predicate,
    object_id,
    source_chunk_id,
    confidence
)
```

This allows graph behaviour to be tested without introducing a dedicated graph server.

---

## 11.2 ArangoDB Evaluation

ArangoDB should only be introduced as a benchmark candidate.

Evaluate:

- idle RAM
- peak RAM
- startup time
- graph query latency
- ingestion throughput
- storage size
- operational complexity

The decision question is not:

> Can ArangoDB run?

It is:

> Does ArangoDB provide enough benefit on Raspberry Pi to justify its permanent resource cost?

---

# 12. Resource Management

Raspberry Pi resource management is part of the architecture, not an optimization step.

## 12.1 Workload Classes

Two main execution modes:

### Query Mode

```text
Question
-> Query Embedding
-> Retrieval
-> Context Construction
-> LLM
-> Answer
```

### Ingestion Mode

```text
Document
-> Parse
-> Chunk
-> Embed
-> Optional KG Extraction
-> Index
```

Heavy ingestion should not compete with interactive chat.

---

## 12.2 Job Queue

Implement a lightweight local queue.

Possible baseline:

```text
SQLite jobs table
+
single worker
```

States:

```text
queued
running
completed
failed
cancelled
```

Job types:

```text
parse
chunk
embed
index
extract_kg
reindex
```

---

## 12.3 Concurrency Policy

Initial policy:

```text
LLM generation:       1
Embedding batch:      1
KG extraction:        1
Heavy ingestion jobs: 1
```

Avoid simultaneous:

```text
LLM Generation
+
Bulk Embedding
+
KG Extraction
+
Large Index Build
```

---

## 12.4 Resource Manager

Later introduce:

```text
ResourceManager
```

Inputs:

- free RAM
- CPU utilization
- CPU temperature
- active LLM session
- ingestion state
- queue length

Possible actions:

- pause ingestion
- delay KG extraction
- reduce embedding batch size
- unload unused model
- reject low-priority job
- lower worker concurrency

---

# 13. Storage Strategy

Benchmark:

```text
MicroSD
USB 3 SSD
NVMe SSD
```

Test:

- boot time
- LLM load time
- embedding model load
- ingestion
- SQLite writes
- vector indexing
- random reads
- graph ingestion
- database query latency
- swap impact
- sustained write behaviour
- temperature

Expected deployment hierarchy:

```text
Development baseline:
MicroSD

Recommended:
USB SSD

Preferred:
NVMe SSD
```

Final choice must be based on measured results.

---

# 14. Frontend Strategy

Frontend is not a compute priority.

Responsibilities of Raspberry Pi:

- API
- retrieval
- databases
- LLM inference
- ingestion

Responsibilities of browser:

- rendering
- Markdown
- graph visualization
- filtering
- client-side interaction

Do not perform graph layout computation on the Pi unless necessary.

Initial UI:

```text
Documents
Chat
System Status
Benchmark Results
```

Later:

```text
Knowledge Graph Explorer
```

Graph renderer candidates can run fully in browser.

---

# 15. Benchmark Methodology

Benchmarks should be reproducible and stored as machine-readable output.

Each benchmark run should record:

```text
timestamp
git_commit
OS
kernel
Pi firmware
CPU governor
cooling configuration
storage type
model
quantization
context length
thread count
dataset size
```

---

## 15.1 Dataset Sizes

At minimum:

```text
1,000 chunks
10,000 chunks
50,000 chunks
100,000 chunks
```

Also record:

- average chunk length
- total tokens
- language distribution
- file count

---

## 15.2 Metrics

### LLM

- load time
- TTFT
- tokens/sec
- prompt tokens/sec
- RAM
- CPU
- temperature

### Embedding

- chunks/sec
- latency
- RAM
- CPU
- temperature

### Retrieval

- P50
- P95
- P99 latency
- Recall@K
- MRR
- nDCG
- RAM
- index size

### Graph

- triple extraction speed
- extraction quality
- triples/sec
- graph query latency
- RAM
- graph storage size

### End-to-End

Measure:

```text
question received
-> retrieval completed
-> prompt ready
-> first token
-> final token
```

Record:

- retrieval latency
- context build time
- TTFT
- total answer time

---

# 16. Evaluation Dataset

Create a project-controlled benchmark corpus.

It should include:

- English documents
- Traditional Chinese documents
- bilingual documents
- factual questions
- multi-document questions
- entity relationship questions
- exact keyword questions
- semantic questions

Each evaluation item:

```json
{
  "question": "...",
  "expected_documents": [],
  "expected_chunks": [],
  "expected_entities": [],
  "reference_answer": "..."
}
```

This makes retrieval comparison measurable instead of subjective.

---

# 17. Implementation Roadmap

## Phase 0 — Raspberry Pi Baseline

Goal:

Establish reliable hardware and software baseline.

Tasks:

- Raspberry Pi OS 64-bit setup
- active cooling
- SSD / NVMe setup
- Python environment
- Node.js if required
- llama.cpp build
- system metrics collection
- benchmark harness
- storage benchmark

Deliverables:

```text
benchmark/hardware/
docs/hardware-baseline.md
scripts/setup_pi.sh
```

Exit criteria:

- stable sustained CPU workload
- no thermal throttling under expected workload
- repeatable benchmark environment

---

## Phase 1 — Local LLM Benchmark

Goal:

Choose the generation runtime and production model class.

Tasks:

- llama.cpp
- Ollama comparison
- 1B / 2B / 3B / 4B
- Q4 / Q5
- optional 7B comparison
- context tests
- thermal tests

Deliverable:

```text
docs/model-selection.md
benchmark/results/llm/
```

Exit criteria:

Select:

```text
Primary LLM
Primary quantization
Primary context length
Runtime
Thread configuration
```

---

## Phase 2 — Minimal Text RAG

Goal:

Build first complete local RAG.

Pipeline:

```text
PDF
-> Parse
-> Chunk
-> Embed
-> Vector Index
-> Retrieve
-> LLM
-> Answer
```

Features:

- upload document
- list documents
- delete document
- rebuild index
- chat
- citations
- streaming output

No Knowledge Graph.

Exit criteria:

A fresh Raspberry Pi can ingest documents and answer grounded questions without any cloud dependency.

---

## Phase 3 — Retrieval Benchmark

Goal:

Find the best retrieval architecture.

Implement:

```text
BM25
Dense
Hybrid
```

Compare:

```text
SQLite FTS5
sqlite-vec
FAISS
Qdrant
LanceDB
```

Do not implement every candidate inside the production application first.

Create isolated benchmark adapters.

Exit criteria:

Choose:

```text
production keyword index
production vector index
fusion strategy
```

---

## Phase 4 — Resource Manager

Goal:

Make the appliance reliable under mixed workloads.

Implement:

- job queue
- ingestion worker
- concurrency limits
- thermal monitoring
- RAM monitoring
- ingestion pause
- process health monitoring
- system status API

Exit criteria:

Chat remains usable during controlled ingestion workloads without OOM or uncontrolled thermal throttling.

---

## Phase 5 — Knowledge Extraction

Goal:

Determine whether Pi-sized models can produce useful triples.

Implement:

```text
Chunk
-> extraction prompt
-> JSON schema
-> validation
-> entity normalization
-> triples
```

Benchmark:

- extraction latency
- triples/min
- malformed output rate
- duplicate entities
- relation quality
- RAM
- temperature

Exit criteria:

Knowledge extraction must demonstrate usable quality at acceptable throughput.

Otherwise this phase remains experimental and is not added to normal ingestion.

---

## Phase 6 — Knowledge Graph

Goal:

Add graph storage and retrieval.

Start:

```text
SQLite Graph
```

Then compare:

```text
ArangoDB
```

Implement:

- entity search
- neighbour traversal
- relationship lookup
- source chunk mapping
- graph visualization API

Exit criteria:

Graph retrieval must answer at least one category of question materially better than text-only hybrid retrieval.

---

## Phase 7 — Graph-Assisted RAG

Goal:

Combine graph evidence with vector/keyword retrieval.

Pipeline:

```text
Question
├─ BM25
├─ Dense Search
└─ Entity Detection
      ↓
   Graph Search

-> Fusion
-> Context Builder
-> LLM
```

Evaluate:

```text
BM25
Dense
Hybrid
Graph
Hybrid + Graph
```

Exit criteria:

Demonstrate measurable retrieval or answer-quality improvement.

---

## Phase 8 — GraphRAG Research

Only begin after Graph-assisted RAG is stable.

Research:

- entity-centric retrieval
- community detection
- graph summaries
- local/global graph queries
- precomputed summaries
- graph expansion
- graph-aware context selection

Avoid blindly reproducing Microsoft/NVIDIA GraphRAG patterns that assume server-class compute.

The Pi version should focus on precomputation and compact graph representations.

---

## Phase 9 — Appliance Deployment

Goal:

A Raspberry Pi can boot into a functional knowledge appliance.

Implement:

- systemd services
- health checks
- auto-start
- persistent storage
- log rotation
- backup
- model management
- update script
- configuration file
- web UI

Startup target:

```text
Power On
-> Linux
-> API
-> Storage
-> Retrieval
-> LLM
-> Web UI Ready
```

Docker Compose should only be adopted where operational simplicity outweighs container overhead.

---

## Phase 10 — Voice Layer

Voice is explicitly after text RAG / GraphRAG.

Pipeline:

```text
Microphone
-> VAD
-> STT / ASR
-> RAG
-> LLM
-> TTS
-> Audio
```

Benchmark:

- real-time factor
- RAM
- CPU
- latency
- thermal impact
- impact on LLM generation

Voice must not reduce core knowledge appliance reliability.

---

# 18. API Scope

Initial API:

```text
POST   /documents
GET    /documents
DELETE /documents/{id}

POST   /documents/{id}/ingest
GET    /jobs
GET    /jobs/{id}

POST   /chat
GET    /health
GET    /metrics
```

Later:

```text
GET  /graph/entities
GET  /graph/entities/{id}
GET  /graph/relationships
POST /graph/query
```

---

# 19. Data Model

Initial SQLite database:

```text
documents
chunks
jobs
settings
benchmark_runs
```

Later:

```text
entities
entity_aliases
relationships
```

Each chunk should retain:

```text
chunk_id
document_id
chunk_index
text
token_count
metadata
embedding_reference
```

All retrieval evidence must map back to source chunks.

---

# 20. Observability

Expose:

```text
CPU %
RAM used
RAM available
CPU temperature
disk usage
active model
model RAM
queue size
current job
query latency
embedding latency
generation tokens/sec
```

Prefer simple local metrics before introducing Prometheus/Grafana.

Possible interface:

```text
GET /metrics
```

plus CLI benchmark output.

---

# 21. Deployment Strategy

Recommended production layout:

```text
Raspberry Pi 5 16GB
+
Active Cooler
+
NVMe SSD
+
64-bit Raspberry Pi OS
```

Native deployment should be the first target.

Example services:

```text
rag-api.service
rag-worker.service
llama-server.service
```

Optional:

```text
nginx.service
```

Avoid Kubernetes.

Avoid service meshes.

Avoid distributed infrastructure patterns that solve problems the appliance does not have.

---

# 22. Performance Budget

Initial engineering target, subject to benchmark revision:

```text
System + API + storage:
< 2 GB RAM

Embedding subsystem:
< 2 GB working RAM

LLM + KV cache:
largest memory consumer

Remaining:
filesystem cache + safety margin
```

System should avoid operating continuously near 16 GB.

A target working ceiling around:

```text
12–13 GB
```

should be evaluated to leave safety headroom.

---

# 23. Testing Strategy

## Unit Tests

- parsers
- chunking
- fusion
- context construction
- schema validation
- graph normalization

## Retrieval Tests

Given a known query:

```text
expected relevant chunk must appear in Top-K
```

## Integration Tests

```text
document
-> ingest
-> retrieve
-> answer
```

## Stress Tests

- 100k chunks
- repeated queries
- ingestion + query contention
- long context
- sustained generation
- high temperature environment

---

# 24. Definition of Success

The project succeeds when a single Raspberry Pi 5 16 GB can:

1. boot independently
2. ingest documents locally
3. build local indexes
4. retrieve relevant information
5. answer using a local LLM
6. operate without cloud AI services
7. maintain stable memory usage
8. avoid uncontrolled thermal throttling
9. expose a usable browser interface
10. produce reproducible benchmark evidence

Advanced success:

11. extract useful knowledge triples locally
12. maintain a usable knowledge graph
13. combine graph + hybrid retrieval
14. demonstrate measurable GraphRAG benefit
15. optionally support local voice interaction

---

# 25. Immediate Next Steps

Implementation should start with these tasks:

```text
[ ] Create repository skeleton
[ ] Write Raspberry Pi environment setup script
[ ] Install / compile llama.cpp
[ ] Select initial 1B–4B GGUF model candidates
[ ] Build LLM benchmark harness
[ ] Benchmark Q4 vs Q5
[ ] Select initial embedding model candidates
[ ] Implement embedding benchmark
[ ] Build SQLite metadata schema
[ ] Implement FTS5 baseline
[ ] Implement first vector adapter
[ ] Build Minimal RAG API
[ ] Create evaluation dataset
[ ] Record all benchmark results
```

The first meaningful milestone is:

> **One Raspberry Pi, one local LLM, one local embedding model, one local SQLite-backed retrieval system, one uploaded document, and one fully grounded answer — with measured latency, RAM and temperature.**

Everything else should build from that baseline.
