import {ChangeEvent, DragEvent, useEffect, useMemo, useState} from 'react'
import {
    ArrowClockwise, ArrowCounterClockwise, CheckCircle, Cpu, Database, DownloadSimple, Eye, FileText,
    FloppyDisk, Graph, ShareNetwork, SlidersHorizontal, Stack, Trash, UploadSimple,
} from '@phosphor-icons/react'
import {api, type DocumentItem, type OllamaModel, type SystemOverview, type TripleExtractionConfig, type TripleItem} from './api'

const ACCEPT = '.txt,.rtf,.csv,.tsv,.log,.md,.markdown,.py,.js,.jsx,.ts,.tsx,.json,.yaml,.yml,.toml,.ini,.conf,.cfg,.sql,.sh,.css,.html,.xml,.env'
const DEFAULT_TRIPLE_PROMPT = `從內容抽取明確、可驗證的知識三元組。只輸出 JSON：{"triples":[{"subject":"實體","predicate":"關係","object":"實體或值"}]}。不可加入內容沒有陳述的知識；沒有三元組時輸出空陣列。`
const DEFAULT_TRIPLE_CONFIG: TripleExtractionConfig = {
    system_prompt: DEFAULT_TRIPLE_PROMPT,
    chunk_size: 900,
    chunk_overlap: 120,
    batch_chunks: 4,
    chat_model: '',
}

function loadTripleConfig(): TripleExtractionConfig {
    try {
        const saved = localStorage.getItem('local-rag-triple-config')
        return saved ? {...DEFAULT_TRIPLE_CONFIG, ...JSON.parse(saved)} : DEFAULT_TRIPLE_CONFIG
    } catch {
        return DEFAULT_TRIPLE_CONFIG
    }
}

function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function StatusBadge({ready, children}: {ready: boolean; children: string}) {
    return <span className={`workflow-badge ${ready ? 'ready' : ''}`}>{ready && <CheckCircle size={14} weight="fill"/>}{children}</span>
}

export function UploadPanel({documents, overview, refresh}: {
    documents: DocumentItem[];
    overview: SystemOverview | null;
    refresh: () => Promise<void>;
}) {
    const [dragging, setDragging] = useState(false)
    const [busy, setBusy] = useState(false)
    const [message, setMessage] = useState('')
    const [selected, setSelected] = useState<DocumentItem | null>(null)

    async function uploadFiles(files: FileList | File[]) {
        if (!files.length) return
        setBusy(true); setMessage(`正在上載 ${files.length} 個文件…`)
        try {
            for (const file of Array.from(files)) await api.upload(file)
            await refresh(); setMessage(`已上載 ${files.length} 個文件，下一步可前往「處理文件」。`)
        } catch (reason) {
            setMessage(reason instanceof Error ? reason.message : '上載失敗')
        } finally {
            setBusy(false)
        }
    }

    function choose(event: ChangeEvent<HTMLInputElement>) {
        if (event.target.files) void uploadFiles(event.target.files)
        event.target.value = ''
    }

    function drop(event: DragEvent<HTMLLabelElement>) {
        event.preventDefault(); setDragging(false); void uploadFiles(event.dataTransfer.files)
    }

    async function remove(item: DocumentItem) {
        if (!window.confirm(`確定刪除「${item.filename}」及其所有索引和圖譜資料？`)) return
        await api.remove(item.document_id); setSelected(null); await refresh()
    }

    return <section className="workflow-section" aria-labelledby="upload-title">
        <div className="section-heading"><div className="section-icon"><UploadSimple size={19}/></div><div>
            <h2 id="upload-title">上載文件</h2><p>先把文件安全地存到 Raspberry Pi；處理工作會在下一步由你啟動。</p>
        </div></div>
        <div className="connection-card"><div className="connection-heading"><div><Database size={19}/><strong>Graph DB Connection</strong></div>
            <StatusBadge ready={Boolean(overview?.arangodb_connected)}>{overview?.arangodb_connected ? '已連線' : '未連線'}</StatusBadge></div>
            <div className="connection-details"><div><span>ArangoDB</span><strong>{overview?.arangodb_database || '正在讀取…'}</strong><small>{overview?.arangodb_url || '—'}</small></div>
                <div><Graph size={18}/><span>節點</span><strong>{overview?.graph_nodes.toLocaleString('zh-Hant') ?? '—'}</strong></div>
                <div><ShareNetwork size={18}/><span>關係</span><strong>{overview?.graph_relationships.toLocaleString('zh-Hant') ?? '—'}</strong></div></div></div>
        <div className="connection-card vector-connection"><div className="connection-heading"><div><Stack size={19}/><strong>Vector DB Connection</strong></div>
            <StatusBadge ready={Boolean(overview?.qdrant_connected)}>{overview?.qdrant_connected ? '已連線' : '未連線'}</StatusBadge></div>
            <div className="connection-details"><div><span>Qdrant Collection</span><strong>{overview?.qdrant_collection || '正在讀取…'}</strong><small>{overview?.qdrant_url || '—'}</small></div>
                <div><Stack size={18}/><span>向量</span><strong>{overview?.vector_count.toLocaleString('zh-Hant') ?? '—'}</strong></div>
                <div><Cpu size={18}/><span>Embedding</span><strong title={overview?.embedding_model}>{overview?.embedding_model || '—'}</strong></div></div></div>
        <label className={`workflow-dropzone ${dragging ? 'dragging' : ''} ${busy ? 'busy' : ''}`}
               onDragOver={event => {event.preventDefault(); setDragging(true)}} onDragLeave={() => setDragging(false)} onDrop={drop}>
            <UploadSimple size={34}/><strong>{busy ? '正在上載…' : '拖放文件到這裡，或按一下選擇檔案'}</strong>
            <span>TXT、RTF、CSV、LOG、MD、程式碼與設定檔 · 每個最多 20 MB</span>
            <input type="file" multiple accept={ACCEPT} disabled={busy} onChange={choose}/>
        </label>
        {message && <p className="workflow-message" role="status">{message}</p>}
        <div className="table-heading"><div><h3>文件佇列</h3><p>{documents.length} 個文件</p></div><button className="quiet-button" onClick={() => void refresh()}><ArrowClockwise size={16}/>重新整理</button></div>
        <div className="data-table-wrap"><table className="data-table"><thead><tr><th>文件</th><th>上載</th><th>處理狀態</th><th>大小</th><th>三元組</th><th>操作</th></tr></thead>
            <tbody>{documents.map(item => <tr key={item.document_id}><td><span className="file-cell"><FileText size={18}/><strong>{item.filename}</strong></span></td>
                <td><StatusBadge ready>已上載</StatusBadge></td><td><StatusBadge ready={item.embeddings_ready && item.triples_ready}>{item.embeddings_ready && item.triples_ready ? '已完成' : '待處理'}</StatusBadge></td>
                <td>{formatBytes(item.size)}</td><td>{item.graph_triple_count}</td><td><div className="row-actions">
                    <button onClick={() => setSelected(item)} aria-label={`檢視 ${item.filename}`}><Eye size={17}/></button>
                    <a href={api.downloadUrl(item.document_id)} download aria-label={`下載 ${item.filename}`}><DownloadSimple size={17}/></a>
                    <button className="danger" onClick={() => void remove(item)} aria-label={`刪除 ${item.filename}`}><Trash size={17}/></button>
                </div></td></tr>)}</tbody></table>{documents.length === 0 && <div className="table-empty">尚未上載文件。</div>}</div>
        {selected && <div className="info-card" role="dialog" aria-label="文件資訊"><button className="info-close" onClick={() => setSelected(null)}>×</button>
            <FileText size={26}/><div><strong>{selected.filename}</strong><span>文件 ID：{selected.document_id}</span><span>{formatBytes(selected.size)} · {selected.chunk_count} 個區塊 · {selected.graph_triple_count} 個三元組</span></div></div>}
    </section>
}

export function ProcessPanel({documents, overview, models, refresh}: {
    documents: DocumentItem[];
    overview: SystemOverview | null;
    models: OllamaModel[];
    refresh: () => Promise<void>;
}) {
    const [mode, setMode] = useState<'triples' | 'embeddings'>('triples')
    const [selected, setSelected] = useState<Set<string>>(new Set())
    const [busy, setBusy] = useState(false)
    const [message, setMessage] = useState('')
    const [tripleConfig, setTripleConfig] = useState<TripleExtractionConfig>(loadTripleConfig)
    const eligible = useMemo(() => documents.filter(item => mode === 'triples' ? !item.triples_ready : !item.embeddings_ready), [documents, mode])
    const chatModels = useMemo(() => models.filter(model => model.name !== overview?.embedding_model && !model.name.toLocaleLowerCase().includes('embed')), [models, overview?.embedding_model])

    useEffect(() => {
        if (!chatModels.length || chatModels.some(model => model.name === tripleConfig.chat_model)) return
        const preferred = chatModels.find(model => model.name === overview?.chat_model)?.name || chatModels[0].name
        setTripleConfig(previous => ({...previous, chat_model: preferred}))
    }, [chatModels, overview?.chat_model, tripleConfig.chat_model])

    async function process() {
        if (!selected.size) return
        if (mode === 'triples' && (!tripleConfig.chat_model || tripleConfig.system_prompt.trim().length < 20 ||
            tripleConfig.chunk_size < 200 || tripleConfig.chunk_size > 4000 ||
            tripleConfig.chunk_overlap < 0 || tripleConfig.chunk_overlap > Math.min(1000, tripleConfig.chunk_size / 2) ||
            tripleConfig.batch_chunks < 1 || tripleConfig.batch_chunks > 16)) {
            setMessage('請檢查 Prompt 及 Chunk 設定範圍。')
            return
        }
        setBusy(true); setMessage(mode === 'triples' ? 'Ollama 正在抽取知識三元組…' : 'Ollama 正在建立 embeddings…')
        try {
            if (mode === 'triples') localStorage.setItem('local-rag-triple-config', JSON.stringify(tripleConfig))
            await api.process([...selected], mode, mode === 'triples' ? tripleConfig : undefined)
            await refresh(); setSelected(new Set()); setMessage('處理完成。')
        } catch (reason) {
            setMessage(reason instanceof Error ? reason.message : '處理失敗')
        } finally { setBusy(false) }
    }

    return <section className="workflow-section"><div className="section-heading"><div className="section-icon"><ArrowClockwise size={19}/></div><div>
        <h2>處理文件</h2><p>把昂貴的模型工作拆開執行，方便控制 Raspberry Pi 的記憶體及處理時間。</p></div></div>
        <div className="runtime-overview"><div className="runtime-card selectable"><span className="runtime-icon"><span className="ollama-icon" aria-hidden="true"/></span><div><label htmlFor="triple-model">三元組模型</label>
            <select id="triple-model" value={tripleConfig.chat_model} disabled={busy || !chatModels.length}
                onChange={event => setTripleConfig(previous => ({...previous, chat_model: event.target.value}))}>
                {!chatModels.length && <option value="">正在讀取 Ollama 模型…</option>}
                {chatModels.map(model => <option value={model.name} key={model.name}>{model.name} · {(model.size / 1024 / 1024 / 1024).toFixed(1)} GB</option>)}</select>
            <span>Ollama · 已安裝模型</span></div></div>
            <div className="runtime-card"><span className="runtime-icon"><Database size={18}/></span><div><small>已預選 Embedding 模型</small>
                <strong>{overview?.embedding_model || '正在讀取…'}</strong><span>Ollama · 寫入 Qdrant</span></div></div>
            <div className="runtime-card"><span className="runtime-icon"><FileText size={18}/></span><div><small>Documents Ready</small>
                <strong>{overview?.documents_ready ?? '—'} 個文件</strong><span>等待完成處理流程</span></div></div></div>
        <div className="subtabs" role="tablist"><button role="tab" aria-selected={mode === 'triples'} onClick={() => {setMode('triples'); setSelected(new Set())}}>三元組抽取</button>
            <button role="tab" aria-selected={mode === 'embeddings'} onClick={() => {setMode('embeddings'); setSelected(new Set())}}>Embeddings</button></div>
        <div className="process-summary"><div><strong>{mode === 'triples' ? '使用 Ollama 抽取 Subject–Predicate–Object' : '建立向量並寫入 Qdrant'}</strong>
            <span>{eligible.length} 個文件等待此步驟</span></div><button className="primary-button compact" disabled={!selected.size || busy} onClick={() => void process()}>{busy ? '處理中…' : `處理已選文件 (${selected.size})`}</button></div>
        {mode === 'triples' && <details className="triple-config" open>
            <summary><span><SlidersHorizontal size={17}/>Prompt 與 Chunk 設定</span><small>設定會在開始抽取時套用</small></summary>
            <div className="triple-config-body">
                <label className="prompt-field"><span>System Prompt</span><textarea value={tripleConfig.system_prompt} disabled={busy}
                    onChange={event => setTripleConfig(previous => ({...previous, system_prompt: event.target.value}))}/>
                    <small>回應必須維持 `triples` JSON 結構，否則該批次不會產生三元組。</small></label>
                <div className="chunk-config-grid">
                    <label><span>Chunk 大小</span><input type="number" min="200" max="4000" step="100" disabled={busy}
                        value={tripleConfig.chunk_size} onChange={event => setTripleConfig(previous => ({...previous, chunk_size: Number(event.target.value)}))}/><small>200–4,000 字元</small></label>
                    <label><span>重疊字元</span><input type="number" min="0" max={Math.min(1000, Math.floor(tripleConfig.chunk_size / 2))} step="20" disabled={busy}
                        value={tripleConfig.chunk_overlap} onChange={event => setTripleConfig(previous => ({...previous, chunk_overlap: Number(event.target.value)}))}/><small>保留跨區塊語境</small></label>
                    <label><span>每批 Chunk</span><input type="number" min="1" max="16" step="1" disabled={busy}
                        value={tripleConfig.batch_chunks} onChange={event => setTripleConfig(previous => ({...previous, batch_chunks: Number(event.target.value)}))}/><small>較小值較省記憶體</small></label>
                </div>
                <div className="config-footer"><span>估計每 64KB 約 {Math.ceil(64000 / Math.max(1, tripleConfig.chunk_size - tripleConfig.chunk_overlap))} 個 chunks</span>
                    <button className="quiet-button" disabled={busy} onClick={() => setTripleConfig({...DEFAULT_TRIPLE_CONFIG,
                        chat_model: overview?.chat_model || chatModels[0]?.name || ''})}><ArrowCounterClockwise size={15}/>重設預設值</button></div>
            </div>
        </details>}
        {message && <p className="workflow-message" role="status">{message}</p>}
        <div className="data-table-wrap"><table className="data-table"><thead><tr><th><input type="checkbox" aria-label="選取全部待處理文件" checked={eligible.length > 0 && selected.size === eligible.length}
            onChange={event => setSelected(event.target.checked ? new Set(eligible.map(item => item.document_id)) : new Set())}/></th><th>文件</th><th>區塊</th><th>Embeddings</th><th>三元組</th></tr></thead>
            <tbody>{documents.map(item => {const ready = mode === 'triples' ? item.triples_ready : item.embeddings_ready; return <tr key={item.document_id}>
                <td><input type="checkbox" disabled={ready || busy} checked={selected.has(item.document_id)} onChange={event => setSelected(previous => {
                    const next = new Set(previous)
                    if (event.target.checked) next.add(item.document_id)
                    else next.delete(item.document_id)
                    return next
                })}/></td>
                <td><span className="file-cell"><FileText size={18}/><strong>{item.filename}</strong></span></td><td>{item.chunk_count || '—'}</td>
                <td><StatusBadge ready={item.embeddings_ready}>{item.embeddings_ready ? '完成' : '未建立'}</StatusBadge></td><td><StatusBadge ready={item.triples_ready}>{item.triples_ready ? `${item.graph_triple_count} 個` : '未抽取'}</StatusBadge></td></tr>})}</tbody></table></div>
    </section>
}

export function TriplesPanel({refreshDocuments}: {refreshDocuments: () => Promise<void>}) {
    const [triples, setTriples] = useState<TripleItem[]>([])
    const [query, setQuery] = useState('')
    const [busy, setBusy] = useState(false)
    const [message, setMessage] = useState('')
    const refresh = async () => setTriples(await api.triples())
    useEffect(() => {void refresh()}, [])
    const filtered = triples.filter(item => `${item.subject} ${item.predicate} ${item.object} ${item.filename}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()))
    const pending = triples.filter(item => !item.stored).length

    async function storeAll() {
        setBusy(true)
        try {const result = await api.storeTriples(); await Promise.all([refresh(), refreshDocuments()]); setMessage(`已把 ${result.stored} 個三元組寫入 ArangoDB。`)}
        catch (reason) {setMessage(reason instanceof Error ? reason.message : '寫入失敗')}
        finally {setBusy(false)}
    }

    return <section className="workflow-section"><div className="section-heading split"><div className="heading-copy"><div className="section-icon"><FloppyDisk size={19}/></div><div>
        <h2>知識三元組</h2><p>審視模型抽取結果，再明確寫入 ArangoDB 圖譜。</p></div></div>
        <button className="primary-button compact" disabled={!pending || busy} onClick={() => void storeAll()}><FloppyDisk size={17}/>{busy ? '正在寫入…' : `全部存入 Graph DB (${pending})`}</button></div>
        {message && <p className="workflow-message" role="status">{message}</p>}
        <div className="table-filters"><input value={query} onChange={event => setQuery(event.target.value)} placeholder="搜尋實體、關係或文件…"/><span>{filtered.length} 個三元組</span></div>
        <div className="data-table-wrap"><table className="data-table triples-table"><thead><tr><th>Subject</th><th>Predicate</th><th>Object</th><th>來源</th><th>Graph DB</th></tr></thead>
            <tbody>{filtered.map(item => <tr key={item.id}><td><strong>{item.subject}</strong></td><td><span className="predicate-pill">{item.predicate}</span></td><td><strong>{item.object}</strong></td>
                <td>{item.filename}<small>區塊 {item.chunk_index}</small></td><td><StatusBadge ready={item.stored}>{item.stored ? '已儲存' : '待寫入'}</StatusBadge></td></tr>)}</tbody></table>
            {!filtered.length && <div className="table-empty">尚未有已抽取的知識三元組。</div>}</div>
    </section>
}
