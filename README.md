# Raspberry Pi 5 本機 RAG

專為 Raspberry Pi 5（16GB、Raspberry Pi OS 64-bit / ARM64）設計的純文字本機 RAG。生成與 embedding 使用主機上的
Ollama，向量資料庫使用 Qdrant，檢索結果交由既有 `Qwen3-Reranker-0.6B` 服務重排序。

## 架構

- `frontend`：React 19 + TypeScript + Vite，Nginx 提供靜態檔及 `/api` reverse proxy
- `backend`：FastAPI，協調上載、embedding、Qdrant 檢索、reranking 與生成
- `chunking-service`：FastAPI 純文字分段服務
- `reranker-service`：既有 Qwen3 reranker，以 Docker service 執行並持久化 Hugging Face 模型快取
- `qdrant`：Docker volume 持久化向量資料
- `arangodb`：以原生 vertex／edge collections 持久化知識圖譜
- `ollama`：在 Raspberry Pi 主機執行，不放入 Docker

## Raspberry Pi 安裝

先安裝 Docker、Docker Compose plugin 及 Ollama，然後拉取模型：

```bash
ollama pull qwen3:4b
ollama pull qwen3-embedding:0.6b
```

讓 Docker 容器可連接主機 Ollama。建立或編輯 systemd override，令 Ollama 監聽區域網路介面：

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

接著執行 `sudo systemctl daemon-reload && sudo systemctl restart ollama`。建議用防火牆只允許可信任 LAN 或 Docker bridge
存取 11434。

首次啟動 `reranker-service` 會下載 `Qwen/Qwen3-Reranker-0.6B` 到 `reranker-models` Docker volume。建立設定並啟動所有容器：

```bash
cp .env.example .env
# 必須先在 .env 設定一個強 ARANGODB_PASSWORD；Compose 會拒絕空密碼
docker compose up --build -d
```

Reranker 模型載入在 Raspberry Pi 上可能需數分鐘；Compose 健康檢查提供最多約 20 分鐘的首次啟動時間，backend 會等待 reranker ready 後才啟動。

開啟 `http://raspberrypi.local:3000`。API 文件在 `http://raspberrypi.local:8080/docs`。

## 文件限制

只接受純文字類型：TXT、RTF、CSV/TSV、LOG、Markdown、常見程式碼與設定檔。Backend 同時檢查副檔名、NUL byte、文字編碼與空內容；預設每檔上限
20MB。PDF、Office 文件、圖片、音訊、影片及其他 binary 格式會回傳 HTTP 415。

## 資料夾匯入

CLI 逐檔使用同一 REST API，因此同樣套用檔案安全檢查：

```bash
python3 -m venv .venv-tools
source .venv-tools/bin/activate
pip install httpx
python scripts/import-folder.py /home/pi/knowledge --recursive
```

## API

- `POST /api/documents`：multipart `file` 上載與建立索引
- `GET /api/documents`：列出文件及區塊數
- `DELETE /api/documents/{id}`：刪除文件所有向量
- `POST /api/query`：`question`、`language`（`zh-Hant`/`follow`）、`depth`
- `GET /api/graph`：列出由文件自動抽取的知識實體與三元組；可用 `document_id` 篩選
- `GET /api/health`：Ollama、Qdrant、reranker、chunker 狀態

## 資源建議

Ollama 與 reranker 不要同時配置過高 parallelism。Pi 5 16GB 建議 Ollama `OLLAMA_NUM_PARALLEL=1`，Qdrant 使用單一
replica；大量文件匯入時以 16 個 chunk 一批呼叫 embedding。模型檔與 Qdrant volume 最好放在 USB 3 SSD / NVMe，而不是 microSD。

上載文件時會使用現有 chat model，每四個 chunk 一批抽取知識三元組並寫入 ArangoDB Graph。可透過
`GRAPH_EXTRACTION_ENABLED=false` 關閉，或調整 `GRAPH_BATCH_CHUNKS` 平衡抽取品質與 Pi 上的處理時間。
