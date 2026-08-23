# AGENT.md

本文件供在此 repository 工作的 coding agent 使用。所有修改必須以實際 codebase 為準，不要假設本專案仍採用早期的「上載即索引」流程。

## 溝通規則

- 無論使用者用甚麼語言提問，盡可能以繁體中文回覆。
- 以資深軟件工程師角度提供具體、可驗證的結果。
- 改動前先理解現有架構及 coding style；避免無關重構。
- 如需要 git commit，commit message 末尾必須加入：

```text
Co-authored-by: Codex <codex@openai.com>
```

## 專案目標

此專案是 Raspberry Pi 5 本機 RAG／Knowledge Graph 應用，核心原則：

- local-first：文件及生成流程預設留在本機
- Raspberry Pi aware：避免不必要 parallelism、記憶體複製及大型 client bundle
- staged workflow：上載、處理、檢查三元組、存入 Graph DB、搜尋互相分離
- observable：UI 必須清楚顯示服務、文件及處理狀態
- truthful UI：任何 selector、slider 或狀態都必須接到真實 backend 行為，不可只做模擬畫面

## 架構邊界

- `frontend/`：React 19 + TypeScript + Vite；Nginx 將 `/api` proxy 到 backend
- `backend/`：FastAPI orchestrator；負責文件、Ollama、Qdrant、ArangoDB、reranker、對話記憶
- `chunking-service/`：只負責文字 chunking
- `reranker-service/`：只負責 Qwen3 reranking
- `scripts/`：操作正式 REST API 的工具
- `start.sh`／`stop.sh`：安全啟停 Compose stack；不得在 stop script 加入預設刪除 volumes 的行為
- `tests/`：backend 純邏輯及儲存層測試

不要把 Ollama 加入 Compose；它預期在 Raspberry Pi host 上執行，由 container 使用 `host.docker.internal` 連接。

## 使用者流程

Tabs 順序不可任意改動：

1. 上載
2. 處理文件
3. 知識三元組
4. 知識圖譜
5. RAG 搜尋

上載只儲存文件；三元組及 embeddings 必須由「處理文件」頁顯式啟動。三元組在使用者按下 `Store All in Graph DB` 前不可自動寫入 ArangoDB。

## Frontend 慣例

- 延續現有 function component、hooks、單引號、4-space indentation 風格。
- API type 及 request 集中放在 `frontend/src/api.ts`。
- 工作流程元件放在 `WorkflowPanels.tsx`；圖譜功能放在 `KnowledgeGraphPanel.tsx`。
- 不要重新加入模擬狀態到 production path；`VITE_DEMO=true` 的 demo data 必須明確隔離。
- 保持可存取性：原生 label、button、select、range，正確的 ARIA role／selected／checked 狀態。
- 長清單使用現有 overflow／content visibility 策略，避免不必要 render。
- 所有頁面使用 `graph-page` 寬度。
- `html` 必須保留永久 scrollbar／stable gutter，避免 tab 切換造成 layout shift。

### 主題

- `Theme` 有 `system`、`light`、`dark` 三種使用者選項。
- system mode 必須解析成 `document.documentElement.dataset.theme` 的 `light` 或 `dark`，並監聽 `prefers-color-scheme` 變化。
- 手動及系統深色必須共用 `:root[data-theme="dark"]` 規則，禁止建立另一套不完整的 system-dark component overrides。
- 主色是 `#c51a4a`。新增互動元件時需同時檢查 hover、focus、disabled 及 dark mode 對比。
- Ollama SVG 透過 CSS mask 使用：處理文件頁繼承 runtime icon 顏色；RAG 頁淺色黑線、深色白線。

### 品牌

- 不要把 Raspberry Pi 官方 Logo 放入 header 或產品品牌。
- 使用指涉字句 `For use with Raspberry Pi 5`，而主產品名稱保持 `Local RAG`。
- 保留 footer 聲明：`Raspberry Pi is a trademark of Raspberry Pi Ltd.`
- 修改相關呈現前重新檢查 Raspberry Pi 官方 trademark rules。

## Backend 慣例

- FastAPI request／response models 放在 `backend/app/schemas.py`。
- 環境設定只經 `backend/app/config.py` 的 `Settings` 存取。
- 阻塞式 SQLite／ArangoDB 操作使用 `asyncio.to_thread`，避免阻塞 event loop。
- 外部 HTTP 錯誤要轉成清楚的 HTTPException，不得暴露密碼或完整內部 exception。
- 使用者選擇 Ollama 模型時，backend 必須再次驗證模型已安裝；不要信任 frontend option list。
- 所有整數參數必須由 Pydantic 設定合理的 `ge`／`le` 邊界。
- 文件上載必須繼續驗證副檔名、NUL byte、encoding、空內容及大小。
- 刪除文件時要同步處理原始檔、metadata、Qdrant points、三元組及 ArangoDB relations。

## Search 語意

- Pure RAG：Top K 控制候選／rerank 結果。
- Graph Search：KNN Neighbors 控制向量候選；Fanout 及 Number of Hops 控制圖譜擴展；Top K 控制 rerank 結果。
- `depth` 控制命中 chunk 附近帶入的 context window，不可成為無作用的 UI。
- embedding 永遠使用 `OLLAMA_EMBED_MODEL`；不可使用使用者選擇的 chat model 產生 vectors。
- conversation history 只可協助理解追問，不可當成知識來源。

## 驗證要求

修改 frontend 後至少執行：

```bash
cd frontend
npm run build
npm run lint
```

修改 backend 或純邏輯後執行：

```bash
python -m pytest
```

如專案 virtualenv 尚未準備：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r chunking-service/requirements.txt pytest
```

Python cache 寫入受限時，可用 `ast.parse` 進行無寫入語法檢查。提交前執行：

```bash
git diff --check
```

涉及實際 UI 或 API 行為時，重建相關 container 並驗證：

```bash
docker compose up -d --build frontend backend
docker compose ps
curl -fsS http://localhost:3000/api/health
```

UI 改動需要檢查：

- desktop 及窄螢幕
- light、dark、system 三種模式
- console errors／warnings
- loading、empty、disabled 及 error states

## 安全及資料保護

- `.env` 可能包含秘密，不要輸出或提交其內容。
- `ARANGODB_PASSWORD` 必須為非空強密碼。
- 不要將 Ollama 11434 暴露到不可信網路。
- 不要執行 `docker compose down -v`、刪除 Docker volumes 或清除上載資料，除非使用者明確要求並確認資料不可恢復。
- repository 可能有使用者未提交的修改；保留所有無關變更。

## 文件同步

新增或改動以下內容時同步更新 `README.md`：

- service、port 或 volume
- 環境變數
- API endpoint／request field
- 支援文件類型
- workflow step
- search parameter 或預設值
- 安裝及驗證指令
