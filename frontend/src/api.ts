export type DocumentItem = {
    document_id: string;
    filename: string;
    size: number;
    chunk_count: number;
    graph_triple_count: number;
    embeddings_ready: boolean;
    triples_ready: boolean;
    graph_stored: boolean;
}
export type Citation = { index: number; filename: string; chunk_index: number; score: number; text: string }
export type QueryResult = { answer: string; citations: Citation[]; session_id: string; rewritten_query?: string | null }
export type ConversationMessage = { role: 'user' | 'assistant'; content: string }
export type Health = { status: string; services: Record<string, boolean> }
export type GraphNode = { id: string; label: string }
export type GraphEdge = {
    id: string;
    source: string;
    target: string;
    predicate: string;
    document_id: string;
    filename: string;
    chunk_index: number;
}
export type KnowledgeGraph = { nodes: GraphNode[]; edges: GraphEdge[] }
export type TripleItem = {
    id: string; subject: string; predicate: string; object: string; document_id: string;
    filename: string; chunk_index: number; stored: boolean;
}

const demoMode = import.meta.env.VITE_DEMO === 'true'
const demoDocuments: DocumentItem[] = [
    {document_id: 'demo-1', filename: '部署筆記.md', size: 12800, chunk_count: 34, graph_triple_count: 3, embeddings_ready: true, triples_ready: true, graph_stored: true},
    {document_id: 'demo-2', filename: '硬件設定.txt', size: 8400, chunk_count: 18, graph_triple_count: 2, embeddings_ready: true, triples_ready: true, graph_stored: false},
    ...Array.from({length: 10}, (_, index) => ({
        document_id: `demo-${index + 3}`,
        filename: `知識文件-${index + 3}.txt`,
        size: 4096,
        chunk_count: 12,
        graph_triple_count: 0,
        embeddings_ready: false,
        triples_ready: false,
        graph_stored: false,
    })),
]

async function request<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, init)
    if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body.detail || `請求失敗（${response.status}）`)
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
}

export const api = {
    health: () => demoMode ? Promise.resolve({
        status: 'ok',
        services: {ollama: true, qdrant: true, arangodb: true, reranker: true, chunking: true}
    }) : request<Health>('/api/health'),
    documents: () => demoMode ? Promise.resolve({documents: demoDocuments, total_chunks: 3846}) : request<{
        documents: DocumentItem[];
        total_chunks: number
    }>('/api/documents'),
    graph: () => demoMode ? Promise.resolve({
        nodes: [
            {id: 'raspberry pi 5', label: 'Raspberry Pi 5'},
            {id: '16gb ram', label: '16GB RAM'},
            {id: 'ollama', label: 'Ollama'},
            {id: 'qdrant', label: 'Qdrant'},
        ],
        edges: [
            {id: '1', source: 'raspberry pi 5', target: '16gb ram', predicate: '配備', document_id: 'demo-1', filename: '部署筆記.md', chunk_index: 3},
            {id: '2', source: 'raspberry pi 5', target: 'ollama', predicate: '執行', document_id: 'demo-1', filename: '部署筆記.md', chunk_index: 7},
            {id: '3', source: 'ollama', target: 'qdrant', predicate: '提供向量給', document_id: 'demo-2', filename: '硬件設定.txt', chunk_index: 4},
        ],
    } satisfies KnowledgeGraph) : request<KnowledgeGraph>('/api/graph'),
    query: (body: { question: string; language: string; depth: string; search_mode: 'pure' | 'graph'; session_id?: string; document_ids?: string[] }) => demoMode ? Promise.resolve({
        answer: '在 Raspberry Pi 5 上執行本機 RAG 服務，建議使用至少 8GB RAM，並配備高速 microSD（A2 或以上）或 SSD 以存放向量資料庫與模型檔案。[1] 啟用 64 位元作業系統、開啟 PCIe Gen 3，可獲得更好的 I/O 與整體效能。[2]',
        citations: [
            {
                index: 1,
                filename: '部署筆記.md',
                chunk_index: 34,
                score: 0.93,
                text: '模型及向量資料建議放在高速 SSD，並為 Ollama 保留足夠記憶體。'
            },
            {
                index: 2,
                filename: '硬件設定.txt',
                chunk_index: 18,
                score: 0.89,
                text: '使用 64 位元系統並開啟 PCIe Gen 3 可改善儲存 I/O。'
            },
        ],
        session_id: body.session_id || 'demo-session',
    }) : request<QueryResult>('/api/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    }),
    upload: (file: File) => {
        const body = new FormData();
        body.append('file', file);
        return request<DocumentItem>('/api/documents', {method: 'POST', body})
    },
    remove: (id: string) => request<void>(`/api/documents/${id}`, {method: 'DELETE'}),
    process: (documentIds: string[], mode: 'embeddings' | 'triples') => request<{documents: DocumentItem[]; total_chunks: number}>('/api/documents/process', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({document_ids: documentIds, mode}),
    }),
    triples: () => demoMode ? Promise.resolve([
        {id: 't1', subject: 'Raspberry Pi 5', predicate: '執行', object: 'Ollama', document_id: 'demo-1', filename: '部署筆記.md', chunk_index: 7, stored: true},
        {id: 't2', subject: 'Ollama', predicate: '提供向量給', object: 'Qdrant', document_id: 'demo-2', filename: '硬件設定.txt', chunk_index: 4, stored: false},
    ] satisfies TripleItem[]) : request<TripleItem[]>('/api/triples'),
    storeTriples: () => request<{stored: number}>('/api/triples/store', {method: 'POST'}),
    downloadUrl: (id: string) => `/api/documents/${id}/download`,
    conversation: (id: string) => request<{ session_id: string; messages: ConversationMessage[] }>(`/api/conversations/${id}`),
    clearConversation: (id: string) => request<void>(`/api/conversations/${id}`, {method: 'DELETE'}),
}
