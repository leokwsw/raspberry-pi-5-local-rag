# Local RAG — for use with Raspberry Pi 5

一套為 Raspberry Pi 5（建議 16GB RAM、64-bit Raspberry Pi OS、ARM64）設計的本機知識庫。系統以 Ollama 執行生成及 embedding、Qdrant 儲存向量、ArangoDB 儲存知識圖譜，並透過 Qwen3 Reranker 改善檢索排序。

所有文件、向量、三元組及對話均保留在本機環境。介面提供繁體中文、深淺色模式及五步工作流程。

## 功能

### 1. 上載

- 拖放或選擇純文字文件
- 查看文件大小、處理狀態、三元組數量
- 查看文件資料、下載或刪除文件
- 查看 ArangoDB 連線、節點及關係數量
- 查看 Qdrant 連線、collection、向量及 embedding 模型

### 2. 處理文件

- `三元組抽取`：選擇 Ollama 生成模型、編輯 system prompt、chunk size、overlap 及 batch size
- `Embeddings`：使用預設 embedding 模型建立向量並寫入 Qdrant
- 上載與處理解耦，使用者可控制 Raspberry Pi 的記憶體及處理負載

### 3. 知識三元組

- 檢查 Subject–Predicate–Object 抽取結果
- 搜尋及檢視來源文件、chunk index、儲存狀態
- 使用 `Store All in Graph DB` 將三元組寫入 ArangoDB

### 4. 知識圖譜

- Force、Tree、Radial 三種 layout
- 2D／3D、全螢幕、搜尋、縮放、節點選取
- 顯示 ArangoDB 節點及關係
- 匯出圖譜資料

### 5. RAG 搜尋

- 選擇 Ollama 回答模型
- `Pure RAG`：Qdrant dense search、BM25、reciprocal rank fusion 及 reranking
- `Graph Search`：在向量檢索上加入 ArangoDB 關係遍歷
- 文件範圍、回答語言、檢索深度及對話記憶
- 顯示答案引用及來源 chunk

進階搜尋參數：

| 模式 | 參數 | 預設 | 範圍 |
| --- | --- | ---: | ---: |
| Pure RAG | Top K Results | 40 | 1–50 |
| Graph Search | KNN Neighbors | 4096 | 256–8192 |
| Graph Search | Fanout | 400 | 50–1000 |
| Graph Search | Number of Hops | 2 | 1–4 |
| Graph Search | Top K Results | 40 | 1–50 |

## 系統架構

```text
Browser :3000
    │
    ▼
React + TypeScript ── Nginx /api proxy
    │
    ▼
FastAPI backend :8080
    ├── Ollama on host :11434
    ├── Qdrant :6333
    ├── ArangoDB :8529
    ├── Chunking service :8082
    └── Qwen3 Reranker service :8081
```

| 元件 | 技術 | 用途 |
| --- | --- | --- |
| `frontend` | React 19、TypeScript、Vite、Nginx | 五步工作流程及圖譜 UI |
| `backend` | FastAPI、SQLite | 文件協調、檢索、生成、metadata 及對話記憶 |
| `chunking-service` | FastAPI | 純文字分段 |
| `reranker-service` | Qwen3-Reranker-0.6B | 對檢索候選重新排序 |
| `qdrant` | Qdrant 1.15 | chunk embeddings |
| `arangodb` | ArangoDB 3.12 | entities 及 relationships |
| `ollama` | 主機服務 | 生成、三元組抽取及 embeddings |

## 需求

- Raspberry Pi 5，建議 16GB RAM
- 64-bit Raspberry Pi OS
- Docker Engine 及 Docker Compose plugin
- Ollama 安裝於主機
- 建議使用 USB 3 SSD 或 NVMe 儲存模型及 Docker volumes

建議模型：

```bash
ollama pull qwen3:4b
ollama pull qwen3-embedding:0.6b
```

亦可安裝其他生成模型；介面會從 Ollama model list 自動載入並排除 embedding 模型。

## 安裝與啟動

1. 讓 Docker container 可以連接主機 Ollama。建立 Ollama systemd override：

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

2. 重新載入 Ollama：

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

請使用防火牆限制 11434，只允許可信任 LAN 或 Docker bridge 存取。

3. 建立環境設定：

```bash
cp .env.example .env
```

設定強密碼：

```dotenv
ARANGODB_PASSWORD=replace-with-a-strong-password
```

4. 啟動：

```bash
./start.sh
```

`start.sh` 會檢查 Docker、Compose、`.env`、ArangoDB 密碼及 host Ollama，預設重新 build 並等待 API ready。

常用選項：

```bash
./start.sh --no-build
./start.sh --pull
./start.sh --no-wait
./start.sh --help
```

首次啟動 reranker 會下載 `Qwen/Qwen3-Reranker-0.6B`，在 Raspberry Pi 上可能需要數分鐘。

5. 開啟：

- UI：`http://raspberrypi.local:3000`
- Backend API docs：`http://raspberrypi.local:8080/docs`
- Qdrant：`http://raspberrypi.local:6333`

停止服務但保留所有資料：

```bash
./stop.sh
```

`stop.sh` 不會停止 host Ollama，亦不會刪除任何 Docker volume。

## 環境設定

| 變數 | 預設／範例 | 說明 |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | 主機 Ollama API |
| `OLLAMA_CHAT_MODEL` | `qwen3:4b` | 預選生成模型 |
| `OLLAMA_EMBED_MODEL` | `qwen3-embedding:0.6b` | embedding 模型 |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant service |
| `QDRANT_COLLECTION` | `local_rag_chunks` | 向量 collection |
| `ARANGODB_URL` | `http://arangodb:8529` | ArangoDB service |
| `ARANGODB_DATABASE` | `local_rag_graph` | Graph database |
| `ARANGODB_PASSWORD` | 必填 | ArangoDB root 密碼 |
| `CHUNKING_URL` | `http://chunking-service:8082` | chunking service |
| `RERANKER_URL` | `http://reranker-service:8081` | reranker service |
| `MAX_UPLOAD_MB` | `20` | 單一文件上限 |
| `MEMORY_MAX_MESSAGES` | `12` | 每個對話保留訊息數量 |
| `RERANK_SCORE_THRESHOLD` | `0.15` | 最低可靠分數 |
| `NEIGHBOR_WINDOW` | `1` | 命中 chunk 的相鄰內容範圍 |

完整設定請參考 `.env.example`。

## 支援文件

接受純文字內容：

- TXT、RTF、CSV、TSV、LOG、Markdown
- Python、JavaScript、TypeScript、JSX、TSX、CSS、HTML、SQL、Shell
- JSON、YAML、TOML、INI、CONF、CFG、XML、`.env`

Backend 會驗證副檔名、NUL byte、文字編碼、空內容及檔案大小。PDF、Office 文件、圖片、音訊、影片及其他 binary 格式會回傳 HTTP 415。

## 資料夾匯入

```bash
python3 -m venv .venv-tools
source .venv-tools/bin/activate
pip install httpx
python scripts/import-folder.py /home/pi/knowledge --recursive
```

匯入工具只負責上載；之後請在「處理文件」頁執行三元組抽取及 embeddings。

## API 摘要

| Method | Endpoint | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 所有服務狀態 |
| GET | `/api/overview` | 模型、Graph DB、Vector DB 統計 |
| GET | `/api/models` | Ollama 已安裝模型 |
| POST | `/api/documents` | 上載文件 |
| GET | `/api/documents` | 文件清單 |
| POST | `/api/documents/process` | 執行 triples 或 embeddings |
| GET | `/api/documents/{id}/download` | 下載原始文件 |
| DELETE | `/api/documents/{id}` | 刪除文件及相關資料 |
| GET | `/api/triples` | 三元組清單 |
| POST | `/api/triples/store` | 將未儲存三元組寫入 ArangoDB |
| GET | `/api/graph` | 知識圖譜資料 |
| POST | `/api/query` | Pure RAG 或 Graph Search |
| GET | `/api/conversations/{session_id}` | 對話記錄 |
| DELETE | `/api/conversations/{session_id}` | 清除對話 |

## 開發與驗證

Frontend：

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run build
```

Backend tests：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r chunking-service/requirements.txt pytest
python -m pytest
```

Docker logs：

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f reranker-service
```

## 資料持久化

Docker volumes：

- `backend-data`：上載文件、文件 metadata、三元組及 SQLite 對話記憶
- `qdrant-data`：向量
- `arangodb-data`：知識圖譜
- `reranker-models`：Hugging Face 模型快取

刪除 volumes 會永久刪除本機知識庫資料，操作前請先備份。

## Raspberry Pi 效能建議

- Ollama 建議 `OLLAMA_NUM_PARALLEL=1`
- 避免同時執行大型生成、embedding 及 reranking 工作
- Graph Search 的 `KNN Neighbors=4096` 適合較完整檢索，但在大型 collection 上會增加 RAM 及延遲；需要時降低此值
- 三元組 batch 建議由 4 開始，再按記憶體調整
- 模型及資料庫 volumes 優先放在 SSD／NVMe，不建議長期使用 microSD

## 疑難排解：ArangoDB／Qdrant 顯示 `Unsupported system page size`

Raspberry Pi 5 的 `kernel_2712` 預設使用 16 KB memory page。部分 ArangoDB 及 Qdrant ARM64 container image 內的 `jemalloc` 按 4 KB page size 編譯，因此服務可能在啟動時立即崩潰：

```text
<jemalloc>: Unsupported system page size
Segmentation fault (core dumped)
Aborted (core dumped)
```

Qdrant 已有相同問題的[官方 issue](https://github.com/qdrant/qdrant/issues/3831)。ArangoDB 的 `cannot start with NUMA numactl --interleave=all` 訊息只代表 container 沒有 `SYS_NICE` capability，並非上述 crash 的根本原因；單獨加入 `cap_add: SYS_NICE` 不會修復 page-size 不相容。

先在 Raspberry Pi 檢查架構、page size 及作業系統：

```bash
uname -m
getconf PAGE_SIZE
cat /etc/os-release
```

如輸出包含 `aarch64` 及 `16384`，即表示目前使用 16 KB page kernel。

### Raspberry Pi OS 64-bit

建議改用 4 KB page 的 `kernel8.img`。先確認 kernel image 存在並備份設定：

```bash
ls -l /boot/firmware/kernel8.img
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup
sudo nano /boot/firmware/config.txt
```

在 `config.txt` 末端加入：

```ini
kernel=kernel8.img
```

重新啟動並確認 page size：

```bash
sudo reboot
getconf PAGE_SIZE
```

預期結果為 `4096`。Raspberry Pi 官方的[kernel 文件](https://www.raspberrypi.com/documentation/computers/linux_kernel.html)列出 `kernel8` 與 Raspberry Pi 5 `kernel_2712` 的不同 build target。

> 如果系統是 Ubuntu 或其他 Linux distribution，請勿直接套用上述 Raspberry Pi OS 設定；應依該 distribution 的方式安裝及選用 4 KB page kernel。

切換 kernel 後重新啟動服務：

```bash
./stop.sh
./start.sh
docker compose ps
docker compose logs --tail=100 arangodb qdrant
```

如果全新安裝曾在 database 初始化途中崩潰，volume 可能只完成部分初始化。確認沒有任何需要保留的資料後，才可刪除 volumes 並重建：

```bash
docker compose down -v
docker compose up -d
```

`docker compose down -v` 會永久刪除 ArangoDB、Qdrant、backend 及其他 Compose volume 資料，已有知識庫時不可執行。

## 商標及資產

本專案以指涉方式說明與 Raspberry Pi 5 的相容性，並非 Raspberry Pi Ltd 官方產品。Raspberry Pi 商標使用應遵守[官方商標規則](https://www.raspberrypi.com/trademark-rules/)。Ollama icon 位於 `frontend/public/ollama-logo.svg`。
