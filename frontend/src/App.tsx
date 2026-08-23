import {ChangeEvent, DragEvent, FormEvent, useCallback, useEffect, useState} from 'react'
import {ArrowSquareOut, FileText, Trash, UploadSimple} from '@phosphor-icons/react'
import {api, type Citation, type DocumentItem, type Health, type KnowledgeGraph, type QueryResult} from './api'
import {KnowledgeGraphPanel} from './KnowledgeGraphPanel'

type Tab = 'chat' | 'documents' | 'graph'
type ChatEntry = { role: 'user' | 'assistant'; content: string; citations?: Citation[] }

const SUPPORTED_FILE_EXTENSIONS = [
    '.txt', '.rtf', '.csv', '.tsv', '.log', '.md', '.markdown', '.py', '.js', '.jsx', '.ts', '.tsx', '.json',
    '.yaml', '.yml', '.toml', '.ini', '.conf', '.cfg', '.sql', '.sh', '.css', '.html', '.xml', '.env',
]
const FILE_ACCEPT = SUPPORTED_FILE_EXTENSIONS.join(',')

function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function Tabs({tab, disabled, onChange}: { tab: Tab; disabled: boolean; onChange: (tab: Tab) => void }) {
    return <div className="tabs" role="tablist" aria-label="知識庫功能">
        <button className="tab" role="tab" aria-selected={tab === 'chat'} disabled={disabled}
                onClick={() => onChange('chat')}>對話</button>
        <button className="tab" role="tab" aria-selected={tab === 'documents'}
                disabled={disabled}
                onClick={() => onChange('documents')}>文件
        </button>
        <button className="tab" role="tab" aria-selected={tab === 'graph'} disabled={disabled}
                onClick={() => onChange('graph')}>圖譜</button>
    </div>
}

function Status({health}: { health: Health | null }) {
    const okay = health?.services && ['ollama', 'qdrant', 'arangodb', 'reranker', 'chunking'].every(key => health.services[key])
    return <footer className="status"><span
        className={okay ? 'status-dot online' : 'status-dot'}/>{okay ? 'Ollama · Qdrant · ArangoDB · 重排序服務 · 分段服務均正常' : '正在檢查本機服務…'}
    </footer>
}

function Sources({citations}: { citations: Citation[] }) {
    return <section className="sources" aria-labelledby="sources-title">
        <h3 id="sources-title">來源</h3>
        <div className="source-list">{citations.map(item => <details className="source"
                                                                     key={`${item.filename}-${item.chunk_index}`}>
            <summary><span><FileText size={18} weight="regular"/>{item.filename}</span><span
                className="chunk">區塊 {item.chunk_index} <ArrowSquareOut size={16}/></span></summary>
            <p>{item.text}</p>
        </details>)}</div>
    </section>
}

function ChatPanel({documents, totalChunks, onLoadingChange}: {
    documents: DocumentItem[];
    totalChunks: number;
    onLoadingChange: (loading: boolean) => void;
}) {
    const [question, setQuestion] = useState('')
    const [language, setLanguage] = useState('zh-Hant')
    const [depth, setDepth] = useState('standard')
    const [documentScope, setDocumentScope] = useState('all')
    const [sessionId, setSessionId] = useState(() => localStorage.getItem('local-rag-session') || '')
    const [entries, setEntries] = useState<ChatEntry[]>([])
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (!sessionId) return
        api.conversation(sessionId)
            .then(data => setEntries(data.messages))
            .catch(() => {
                localStorage.removeItem('local-rag-session')
                setSessionId('')
            })
    }, [sessionId])

    async function submit(event: FormEvent) {
        event.preventDefault();
        if (!question.trim()) return
        setLoading(true);
        onLoadingChange(true)
        setError('')
        try {
            const submittedQuestion = question.trim()
            const result: QueryResult = await api.query({
                question: submittedQuestion,
                language,
                depth,
                session_id: sessionId || undefined,
                document_ids: documentScope === 'all' ? [] : [documentScope],
            })
            localStorage.setItem('local-rag-session', result.session_id)
            setSessionId(result.session_id)
            setEntries(previous => [
                ...previous,
                {role: 'user', content: submittedQuestion},
                {role: 'assistant', content: result.answer, citations: result.citations},
            ])
            setQuestion('')
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : '查詢失敗')
        } finally {
            setLoading(false)
            onLoadingChange(false)
        }
    }

    async function newConversation() {
        if (loading) return
        if (sessionId) await api.clearConversation(sessionId).catch(() => undefined)
        localStorage.removeItem('local-rag-session')
        setSessionId('')
        setEntries([])
        setError('')
    }

    return <>
        <div className="chat-toolbar"><div className="library-meta"><FileText size={18}/>{documents.length} 個文件
            · {totalChunks.toLocaleString('zh-Hant')} 個區塊 · 剛剛同步
        </div><button type="button" className="secondary-button" disabled={loading || entries.length === 0}
                      onClick={newConversation}>新對話</button>
        </div>
        {entries.length > 0 && <section className="conversation" aria-label="對話記錄">{entries.map((entry, index) =>
            <article className={`message ${entry.role}`} key={`${entry.role}-${index}`}>
                <div className="message-label">{entry.role === 'user' ? '你' : '本機 RAG'}</div>
                <div className="message-body">{entry.content}</div>
                {entry.citations?.length ? <Sources citations={entry.citations}/> : null}
            </article>)}</section>}
        <form onSubmit={submit}>
            <label htmlFor="question">向文件提問</label>
            <textarea id="question" value={question} disabled={loading}
                      onChange={event => setQuestion(event.target.value)}
                      placeholder="輸入你想查詢的內容…" required/>
            <div className="fields">
                <div><label htmlFor="language">回答語言</label><select id="language" value={language} disabled={loading}
                                                                       onChange={event => setLanguage(event.target.value)}>
                    <option value="zh-Hant">繁體中文</option>
                    <option value="follow">跟隨提問語言</option>
                </select></div>
                <div><label htmlFor="depth">檢索深度</label><select id="depth" value={depth} disabled={loading}
                                                                    onChange={event => setDepth(event.target.value)}>
                    <option value="quick">快速</option>
                    <option value="standard">標準</option>
                    <option value="deep">深入</option>
                </select></div>
                <div><label htmlFor="document-scope">文件範圍</label><select id="document-scope" value={documentScope}
                                                                              disabled={loading}
                                                                              onChange={event => setDocumentScope(event.target.value)}>
                    <option value="all">所有文件</option>
                    {documents.map(item => <option value={item.document_id} key={item.document_id}>{item.filename}</option>)}
                </select></div>
            </div>
            <button className="primary"
                    disabled={loading || !question.trim()}>{loading && <span className="button-spinner" aria-hidden="true"/>}
                {loading ? '正在生成答案…' : '取得答案'}</button>
        </form>
        {error && <p className="error" role="alert">{error}</p>}
    </>
}

function DocumentsPanel({documents, refresh}: { documents: DocumentItem[]; refresh: () => Promise<void> }) {
    const [busy, setBusy] = useState(false)
    const [dragging, setDragging] = useState(false)
    const [message, setMessage] = useState('')
    const uploadFiles = async (files: File[]) => {
        if (!files.length) return
        const supportedFiles = files.filter(file => SUPPORTED_FILE_EXTENSIONS.some(extension => file.name.toLowerCase().endsWith(extension)))
        const skippedCount = files.length - supportedFiles.length
        if (!supportedFiles.length) {
            setMessage('沒有可上載的純文字檔案，請檢查檔案類型。')
            return
        }
        setBusy(true);
        setMessage(`正在建立 ${supportedFiles.length} 個文件的索引…`)
        try {
            for (const file of supportedFiles) await api.upload(file);
            await refresh();
            setMessage(`已完成 ${supportedFiles.length} 個文件${skippedCount ? `，略過 ${skippedCount} 個不支援的檔案` : ''}`)
        } catch (reason) {
            setMessage(reason instanceof Error ? reason.message : '上載失敗')
        } finally {
            setBusy(false)
        }
    }
    const upload = async (event: ChangeEvent<HTMLInputElement>) => {
        await uploadFiles(Array.from(event.target.files || []))
        event.target.value = ''
    }
    const drop = (event: DragEvent<HTMLLabelElement>) => {
        event.preventDefault()
        event.stopPropagation()
        setDragging(false)
        if (!busy) void uploadFiles(Array.from(event.dataTransfer.files))
    }
    const remove = async (item: DocumentItem) => {
        if (!window.confirm(`確定移除「${item.filename}」？`)) return;
        await api.remove(item.document_id);
        await refresh()
    }
    return <section className="documents-panel">
        <label className={`dropzone ${busy ? 'busy' : ''} ${dragging ? 'dragging' : ''}`}
               onDragEnter={event => {
                   event.preventDefault()
                   if (!busy) setDragging(true)
               }}
               onDragOver={event => {
                   event.preventDefault()
                   event.dataTransfer.dropEffect = 'copy'
               }}
               onDragLeave={event => {
                   event.preventDefault()
                   if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false)
               }}
               onDrop={drop}><UploadSimple
            size={34}/><strong>{busy ? '正在處理文件…' : '拖放文件到這裡，或選擇檔案'}</strong><span>TXT、RTF、CSV、LOG、MD、程式碼與設定檔</span><input
            type="file" multiple disabled={busy} onChange={upload}
            accept={FILE_ACCEPT}/></label>
        {message && <p className="upload-message" role="status">{message}</p>}
        <h2>已建立索引</h2>
        {documents.length === 0 ? <p className="empty">尚未加入文件。</p> :
            <div className="document-list">{documents.map(item => <div className="document-row" key={item.document_id}>
                <FileText size={20}/><span
                className="document-name">{item.filename}</span><span>{formatBytes(item.size)}</span><span>{item.chunk_count} 個區塊</span>
                <span>{item.graph_triple_count} 個關係</span>
                <button className="icon-button" onClick={() => remove(item)} aria-label={`移除 ${item.filename}`}><Trash
                    size={18}/></button>
            </div>)}</div>}
    </section>
}

export function App() {
    const [tab, setTab] = useState<Tab>('chat')
    const [queryLoading, setQueryLoading] = useState(false)
    const [documents, setDocuments] = useState<DocumentItem[]>([])
    const [totalChunks, setTotalChunks] = useState(0)
    const [health, setHealth] = useState<Health | null>(null)
    const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
    const [graphLoading, setGraphLoading] = useState(false)
    const [graphError, setGraphError] = useState('')
    const refresh = useCallback(async () => {
        const data = await api.documents();
        setDocuments(data.documents);
        setTotalChunks(data.total_chunks)
    }, [])
    useEffect(() => {
        refresh().catch(() => undefined);
        api.health().then(setHealth).catch(() => undefined)
    }, [refresh])
    useEffect(() => {
        if (tab !== 'graph') return
        setGraphLoading(true)
        setGraphError('')
        api.graph().then(setGraph).catch(reason => setGraphError(reason instanceof Error ? reason.message : '載入圖譜失敗'))
            .finally(() => setGraphLoading(false))
    }, [tab, documents])
    const subtitle = tab === 'chat' ? '匯入純文字，然後向你的私人知識庫提問。' :
        tab === 'documents' ? '只需純文字，就能建立你的私人檢索資料庫。' : '探索文件中的實體及其關係。'
    return <main className={tab === 'graph' ? 'graph-page' : ''}>
        <header><h1>Raspberry Pi 5 Local RAG</h1><p>{subtitle}</p></header>
        <section className="panel"><Tabs tab={tab} disabled={queryLoading} onChange={setTab}/>{tab === 'chat' ?
            <ChatPanel documents={documents} totalChunks={totalChunks} onLoadingChange={setQueryLoading}/> : tab === 'documents' ?
            <DocumentsPanel documents={documents} refresh={refresh}/> :
            <KnowledgeGraphPanel graph={graph} loading={graphLoading} error={graphError}/>}<Status health={health}/></section>
    </main>
}
