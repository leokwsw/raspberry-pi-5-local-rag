# AGENTS.md

## 專案目標

這個 repo 的目標是在本機 Raspberry Pi 5 16GB 上，用 Ollama 與 ChromaDB 建立一個小型 RAG AI application。專案應保持輕量、可離線執行、容易在邊緣裝置上維護。

核心檔案：

- `app.py`: CLI RAG 應用，負責建立知識庫、向量檢索、組 prompt 與呼叫 Ollama。
- `README.md`: 使用者安裝、模型準備與執行說明。
- `requirements.txt`: Python 依賴，目前只有 `chromadb` 與 `ollama`。

## 技術選擇

- Python 3.10+。
- Ollama 作為本機 embedding 與 LLM runtime。
- `nomic-embed-text` 作為預設 embedding model。
- `llama3.2:3b` 作為 Raspberry Pi 5 16GB 上較務實的預設生成模型。
- ChromaDB 使用本機 persistent storage，預設資料夾為 `./chroma_db`。

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

執行互動模式：

```sh
python3 app.py
```

單次提問：

```sh
python3 app.py --question "Raspberry Pi 5 適合跑本機 RAG 嗎？"
```

重建索引：

```sh
python3 app.py --rebuild
```

語法檢查：

```sh
python3 -m py_compile app.py
```

## 開發守則

- 優先維持單檔 CLI 範例，除非需求明確，不要加入 web framework 或服務化架構。
- 修改 RAG 行為時，保留清楚的階段：文件載入、embedding、ChromaDB upsert、query retrieval、LLM generation。
- 新增模型、資料來源、參數或 storage 路徑時，同步更新 `README.md` 與本檔。
- 不要提交 `.venv`、模型檔、本機 ChromaDB 資料、暫存檔或 IDE 設定。
- 這個專案依賴本機 Ollama daemon；若無法實際執行，回覆中要說明缺少的服務或模型。
- 保持適合 Raspberry Pi 5 16GB 的資源用量，預設 `top_k`、prompt context 與模型選擇都應保守。
