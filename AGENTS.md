# AGENTS.md

## 專案目標

這個 repo 的目標是在本機 Raspberry Pi 5 16GB 上，用 Ollama 與 ChromaDB 建立一個小型 RAG AI application。專案應保持輕量、可離線執行、容易在邊緣裝置上維護。

目前提供三個使用入口：

- CLI version: `app.py`
- Basic Web GUI version: `app_gradio.py`
- Enhanced Web GUI version: `web_gui.py` (含資料集管理、對話歷史、Feedback RAG、知識圖譜)

## 核心檔案

- `app.py`: CLI RAG 應用，負責建立知識庫、向量檢索、組 prompt 與呼叫 Ollama。
- `app_gradio.py`: 基本 Gradio Web GUI，重用 `app.py` 的 `LocalRAG` pipeline。
- `web_gui.py`: 完整功能 Gradio Web GUI，使用 `enhanced_rag.py` 提供進階功能。
- `enhanced_rag.py`: 增強版 RAG 引擎，整合 Feedback RAG 與知識圖譜。
- `storage.py`: SQLite 儲存層，管理對話歷史、回饋、文件、實體與關係。
- `media_processor.py`: 多媒體處理模組，支援文字、音訊、影片轉錄。
- `README.md`: 使用者安裝、模型準備與執行說明。
- `requirements.txt`: Python 依賴，包含 `chromadb`、`ollama` 與 `gradio`。

## 技術選擇

- Python 3.10+。
- Ollama 作為本機模型 runtime，執行三個模型：
  - `nomic-embed-text`：Embedding model（向量嵌入）
  - `llama3.2:3b`：LLM model（生成回答）
  - `bge-reranker-base`：Reranking model（重新排序，可選）
- ChromaDB 作為 Vector DB，使用本機 persistent storage，預設資料夾為 `./chroma_db`。
- SQLite 作為 Graph DB 與 metadata 儲存（實體、關係、對話、回饋），預設資料夾為 `./rag_storage`。
- Gradio 提供本機 Web GUI，預設 host `0.0.0.0`、port `7860`。
- `EnhancedRAG.stream_answer()` 與 `LocalRAG.stream_answer()` 提供 streaming output。

## 常用命令

### 使用 Shell Scripts（推薦）

```sh
./setup.sh       # 安裝依賴、下載模型
./run.sh         # 啟動 Web GUI
./run.sh --cli   # 啟動 CLI 模式
./stop.sh        # 停止服務
./stop.sh --all  # 停止服務與 Ollama
```

### 手動建立環境

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

準備 Ollama 模型（三個模型）：

```sh
ollama pull nomic-embed-text    # Embedding
ollama pull llama3.2:3b         # LLM
ollama pull bge-reranker-base   # Reranking（可選）
```

執行 CLI 互動模式：

```sh
python3 app.py
```

單次提問：

```sh
python3 app.py --question "Raspberry Pi 5 適合跑本機 RAG 嗎？"
```

串流輸出：

```sh
python3 app.py --question "RAG 的基本流程是什麼？" --stream
```

執行基本 Gradio Web GUI：

```sh
python3 app_gradio.py
```

執行增強版 Gradio Web GUI：

```sh
python3 web_gui.py
```

指定 host / port：

```sh
python3 web_gui.py --host 0.0.0.0 --port 7860
```

停用 Feedback RAG 或知識圖譜：

```sh
python3 web_gui.py --no-feedback --no-graph
```

重建索引：

```sh
python3 app.py --rebuild
python3 app_gradio.py --rebuild
python3 web_gui.py --rebuild
```

語法檢查：

```sh
python3 -m py_compile app.py
python3 -m py_compile app_gradio.py
python3 -m py_compile web_gui.py
python3 -m py_compile enhanced_rag.py
python3 -m py_compile storage.py
python3 -m py_compile media_processor.py
```

## 開發守則

- 保留三個入口：`app.py` 是 CLI，`app_gradio.py` 是基本 Web GUI，`web_gui.py` 是增強版 Web GUI。
- 基本 Gradio Web GUI 應重用 `app.py` 的 `LocalRAG`。
- 增強版 Web GUI 應使用 `enhanced_rag.py` 的 `EnhancedRAG`。
- 串流輸出應使用 `stream_answer()` method。
- 修改 RAG 行為時，保留清楚的階段：文件載入、embedding、ChromaDB upsert、query retrieval、LLM generation。
- Feedback RAG 邏輯在 `enhanced_rag.py`，使用 `storage.py` 的 `get_source_feedback_scores()` 調整檢索分數。
- 知識圖譜使用 SQLite 儲存實體與關係，透過 `storage.py` 的 Entity 與 Relationship 資料結構。
- 多媒體處理使用 `media_processor.py`，支援文字、音訊（Whisper）、影片（FFmpeg + Whisper）。
- 新增模型、資料來源、參數或 storage 路徑時，同步更新 `README.md` 與本檔。
- 不要提交 `.venv`、模型檔、本機 ChromaDB 資料、SQLite 資料庫、暫存檔或 IDE 設定。
- 這個專案依賴本機 Ollama daemon；若無法實際執行，回覆中要說明缺少的服務或模型。
- 保持適合 Raspberry Pi 5 16GB 的資源用量，預設 `top_k`、prompt context 與模型選擇都應保守。

## 驗證建議

一般程式修改至少執行：

```sh
python3 -m py_compile app.py app_gradio.py web_gui.py enhanced_rag.py storage.py media_processor.py
python3 app.py --help
python3 app_gradio.py --help
python3 web_gui.py --help
```

若本機已安裝依賴、Ollama 已啟動且模型已下載，再實測：

```sh
python3 app.py --question "RAG 的基本流程是什麼？" --stream
python3 web_gui.py
```

## 資料夾結構

```
.
├── setup.sh            # 安裝腳本
├── run.sh              # 啟動腳本
├── stop.sh             # 停止腳本
├── app.py              # CLI 入口
├── app_gradio.py       # 基本 Web GUI
├── web_gui.py          # 增強版 Web GUI
├── enhanced_rag.py     # 增強版 RAG 引擎（含 Reranking）
├── storage.py          # SQLite 儲存層（Graph DB）
├── media_processor.py  # 多媒體處理
├── requirements.txt    # Python 依賴
├── README.md           # 使用說明
├── AGENTS.md           # 開發指南
├── .gitignore          # Git 忽略設定
├── chroma_db/          # ChromaDB 向量資料庫 (gitignore)
├── rag_storage/        # SQLite Graph DB / metadata (gitignore)
└── uploads/            # 上傳檔案暫存 (gitignore)
```
