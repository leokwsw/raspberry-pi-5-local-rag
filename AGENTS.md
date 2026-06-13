# AGENTS.md

## 專案目標

這個 repo 的目標是在本機 Raspberry Pi 5 16GB 上，用 Ollama 與 ChromaDB 建立一個小型 RAG AI application。專案應保持輕量、可離線執行、容易在邊緣裝置上維護。

目前提供兩個使用入口：

- CLI version: `app.py`
- Web GUI version: `app_gradio.py`

## 核心檔案

- `app.py`: CLI RAG 應用，負責建立知識庫、向量檢索、組 prompt 與呼叫 Ollama。
- `app_gradio.py`: Gradio Web GUI，重用 `app.py` 的 `LocalRAG` pipeline。
- `README.md`: 使用者安裝、模型準備與執行說明。
- `requirements.txt`: Python 依賴，包含 `chromadb`、`ollama` 與 `gradio`。
- `img/screencap.png`: README 使用的 CLI running sample 截圖。

## 技術選擇

- Python 3.10+。
- Ollama 作為本機 embedding 與 LLM runtime。
- `nomic-embed-text` 作為預設 embedding model。
- `llama3.2:3b` 作為 Raspberry Pi 5 16GB 上較務實的預設生成模型。
- ChromaDB 使用本機 persistent storage，預設資料夾為 `./chroma_db`。
- Gradio 提供本機 Web GUI，預設 host `0.0.0.0`、port `7860`。
- `LocalRAG.stream_answer()` 提供 streaming output，CLI 透過 stdout 串流，Gradio 透過 generator + queue 串流更新畫面。

## 常用命令

建立環境：

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

準備 Ollama 模型：

```sh
ollama pull nomic-embed-text
ollama pull llama3.2:3b
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

執行 Gradio Web GUI：

```sh
python3 app_gradio.py
```

指定 Gradio host / port：

```sh
python3 app_gradio.py --host 0.0.0.0 --port 7860
```

重建索引：

```sh
python3 app.py --rebuild
python3 app_gradio.py --rebuild
```

語法檢查：

```sh
python3 -m py_compile app.py
python3 -m py_compile app_gradio.py
```

## 開發守則

- 保留兩個入口：`app.py` 是 CLI，`app_gradio.py` 是 Web GUI。不要把 CLI 行為破壞掉。
- Gradio Web GUI 應重用 `app.py` 的 `LocalRAG`，避免複製 RAG pipeline。
- 串流輸出應使用 `LocalRAG.stream_answer()`；CLI 用 stdout streaming，Gradio 用 generator streaming。若要標準 SSE，應新增獨立 API 入口並重用同一個 method。
- 修改 RAG 行為時，保留清楚的階段：文件載入、embedding、ChromaDB upsert、query retrieval、LLM generation。
- 新增模型、資料來源、參數或 storage 路徑時，同步更新 `README.md` 與本檔。
- 不要提交 `.venv`、模型檔、本機 ChromaDB 資料、暫存檔或 IDE 設定。
- 這個專案依賴本機 Ollama daemon；若無法實際執行，回覆中要說明缺少的服務或模型。
- 保持適合 Raspberry Pi 5 16GB 的資源用量，預設 `top_k`、prompt context 與模型選擇都應保守。

## 驗證建議

一般程式修改至少執行：

```sh
python3 -m py_compile app.py app_gradio.py
python3 app.py --help
python3 app_gradio.py --help
```

若本機已安裝依賴、Ollama 已啟動且模型已下載，再實測：

```sh
python3 app.py --question "RAG 的基本流程是什麼？" --stream
python3 app_gradio.py
```
