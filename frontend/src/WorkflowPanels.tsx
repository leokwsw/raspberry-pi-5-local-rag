import {ChangeEvent, DragEvent, useEffect, useMemo, useState} from 'react'
import {
    ArrowClockwise, CheckCircle, DownloadSimple, Eye, FileText, FloppyDisk, Trash, UploadSimple,
} from '@phosphor-icons/react'
import {api, type DocumentItem, type TripleItem} from './api'

const ACCEPT = '.txt,.rtf,.csv,.tsv,.log,.md,.markdown,.py,.js,.jsx,.ts,.tsx,.json,.yaml,.yml,.toml,.ini,.conf,.cfg,.sql,.sh,.css,.html,.xml,.env'

function formatBytes(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function StatusBadge({ready, children}: {ready: boolean; children: string}) {
    return <span className={`workflow-badge ${ready ? 'ready' : ''}`}>{ready && <CheckCircle size={14} weight="fill"/>}{children}</span>
}

export function UploadPanel({documents, refresh}: {documents: DocumentItem[]; refresh: () => Promise<void>}) {
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

export function ProcessPanel({documents, refresh}: {documents: DocumentItem[]; refresh: () => Promise<void>}) {
    const [mode, setMode] = useState<'triples' | 'embeddings'>('triples')
    const [selected, setSelected] = useState<Set<string>>(new Set())
    const [busy, setBusy] = useState(false)
    const [message, setMessage] = useState('')
    const eligible = useMemo(() => documents.filter(item => mode === 'triples' ? !item.triples_ready : !item.embeddings_ready), [documents, mode])

    async function process() {
        if (!selected.size) return
        setBusy(true); setMessage(mode === 'triples' ? 'Ollama 正在抽取知識三元組…' : 'Ollama 正在建立 embeddings…')
        try {
            await api.process([...selected], mode); await refresh(); setSelected(new Set()); setMessage('處理完成。')
        } catch (reason) {
            setMessage(reason instanceof Error ? reason.message : '處理失敗')
        } finally { setBusy(false) }
    }

    return <section className="workflow-section"><div className="section-heading"><div className="section-icon"><ArrowClockwise size={19}/></div><div>
        <h2>處理文件</h2><p>把昂貴的模型工作拆開執行，方便控制 Raspberry Pi 的記憶體及處理時間。</p></div></div>
        <div className="subtabs" role="tablist"><button role="tab" aria-selected={mode === 'triples'} onClick={() => {setMode('triples'); setSelected(new Set())}}>三元組抽取</button>
            <button role="tab" aria-selected={mode === 'embeddings'} onClick={() => {setMode('embeddings'); setSelected(new Set())}}>Embeddings</button></div>
        <div className="process-summary"><div><strong>{mode === 'triples' ? '使用 Ollama 抽取 Subject–Predicate–Object' : '建立向量並寫入 Qdrant'}</strong>
            <span>{eligible.length} 個文件等待此步驟</span></div><button className="primary-button compact" disabled={!selected.size || busy} onClick={() => void process()}>{busy ? '處理中…' : `處理已選文件 (${selected.size})`}</button></div>
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
