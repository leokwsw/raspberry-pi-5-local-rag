import {FormEvent, useCallback, useEffect, useState} from 'react'
import {ArrowSquareOut, FileText} from '@phosphor-icons/react'
import {api, type Citation, type DocumentItem, type Health, type KnowledgeGraph, type OllamaModel, type QueryResult, type SystemOverview} from './api'
import {KnowledgeGraphPanel} from './KnowledgeGraphPanel'
import {ProcessPanel, TriplesPanel, UploadPanel} from './WorkflowPanels'

type Tab = 'upload' | 'process' | 'triples' | 'graph' | 'rag'
type ChatEntry = { role: 'user' | 'assistant'; content: string; citations?: Citation[] }

function Tabs({tab, disabled, onChange}: { tab: Tab; disabled: boolean; onChange: (tab: Tab) => void }) {
    return <div className="tabs workflow-tabs" role="tablist" aria-label="知識庫工作流程">
        <button className="tab" role="tab" aria-selected={tab === 'upload'} disabled={disabled} onClick={() => onChange('upload')}><span>1</span>上載</button>
        <button className="tab" role="tab" aria-selected={tab === 'process'} disabled={disabled} onClick={() => onChange('process')}><span>2</span>處理文件</button>
        <button className="tab" role="tab" aria-selected={tab === 'triples'} disabled={disabled} onClick={() => onChange('triples')}><span>3</span>知識三元組</button>
        <button className="tab" role="tab" aria-selected={tab === 'graph'} disabled={disabled}
                onClick={() => onChange('graph')}><span>4</span>知識圖譜</button>
        <button className="tab" role="tab" aria-selected={tab === 'rag'} disabled={disabled} onClick={() => onChange('rag')}><span>5</span>RAG 搜尋</button>
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
    const [searchMode, setSearchMode] = useState<'pure' | 'graph'>('pure')
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
                search_mode: searchMode,
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
        <div className="rag-mode-switch" role="radiogroup" aria-label="搜尋模式"><button role="radio" aria-checked={searchMode === 'pure'} onClick={() => setSearchMode('pure')}>
            <strong>Pure RAG</strong><span>只以 Qdrant 文件內容檢索</span></button><button role="radio" aria-checked={searchMode === 'graph'} onClick={() => setSearchMode('graph')}>
            <strong>Graph Search</strong><span>結合 ArangoDB 實體關係</span></button></div>
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

export function App() {
    const [tab, setTab] = useState<Tab>('upload')
    const [queryLoading, setQueryLoading] = useState(false)
    const [documents, setDocuments] = useState<DocumentItem[]>([])
    const [totalChunks, setTotalChunks] = useState(0)
    const [health, setHealth] = useState<Health | null>(null)
    const [overview, setOverview] = useState<SystemOverview | null>(null)
    const [models, setModels] = useState<OllamaModel[]>([])
    const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
    const [graphLoading, setGraphLoading] = useState(false)
    const [graphError, setGraphError] = useState('')
    const refresh = useCallback(async () => {
        const [data, systemOverview] = await Promise.all([api.documents(), api.overview()]);
        setDocuments(data.documents);
        setTotalChunks(data.total_chunks)
        setOverview(systemOverview)
    }, [])
    useEffect(() => {
        refresh().catch(() => undefined);
        Promise.all([api.health(), api.models()]).then(([serviceHealth, installedModels]) => {
            setHealth(serviceHealth); setModels(installedModels)
        }).catch(() => undefined)
    }, [refresh])
    useEffect(() => {
        if (tab !== 'graph') return
        setGraphLoading(true)
        setGraphError('')
        api.graph().then(setGraph).catch(reason => setGraphError(reason instanceof Error ? reason.message : '載入圖譜失敗'))
            .finally(() => setGraphLoading(false))
    }, [tab, documents])
    const subtitles: Record<Tab, string> = {
        upload: '從上載到搜尋，每一步都由你掌握。', process: '按 Raspberry Pi 的資源節奏處理文件。',
        triples: '檢查實體關係，再存入 ArangoDB。', graph: '探索文件中的實體及其關係。',
        rag: '使用純向量 RAG，或加入知識圖譜關係搜尋。',
    }
    return <main className="graph-page">
        <header><h1>Raspberry Pi 5 Local RAG</h1><p>{subtitles[tab]}</p></header>
        <section className="panel"><Tabs tab={tab} disabled={queryLoading} onChange={setTab}/>
            {tab === 'upload' ? <UploadPanel documents={documents} overview={overview} refresh={refresh}/> :
                tab === 'process' ? <ProcessPanel documents={documents} overview={overview} models={models} refresh={refresh}/> :
                tab === 'triples' ? <TriplesPanel refreshDocuments={refresh}/> :
                tab === 'graph' ? <KnowledgeGraphPanel graph={graph} loading={graphLoading} error={graphError}/> :
                <ChatPanel documents={documents} totalChunks={totalChunks} onLoadingChange={setQueryLoading}/>}<Status health={health}/></section>
    </main>
}
