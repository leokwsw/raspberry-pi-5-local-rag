import {useEffect, useMemo, useRef, useState} from 'react'
import {
    CornersIn, CornersOut, Cube, Database, DownloadSimple, Eye, MagnifyingGlass, Minus, Plus,
} from '@phosphor-icons/react'
import {
    forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, type SimulationLinkDatum,
    type SimulationNodeDatum,
} from 'd3-force'
import type {KnowledgeGraph} from './api'

type LayoutType = 'force' | 'hierarchical' | 'radial'
type PositionedNode = SimulationNodeDatum & { id: string; label: string; connections: number }
type PositionedLink = SimulationLinkDatum<PositionedNode> & { id: string; predicate: string }

const VIEW_WIDTH = 900
const VIEW_HEIGHT = 520
const NODE_STEP = 25

function download(filename: string, content: string, type: string) {
    const url = URL.createObjectURL(new Blob([content], {type}))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
}

export function KnowledgeGraphPanel({graph, loading, error}: {
    graph: KnowledgeGraph | null;
    loading: boolean;
    error: string;
}) {
    const panelRef = useRef<HTMLElement>(null)
    const searchRef = useRef<HTMLInputElement>(null)
    const [layout, setLayout] = useState<LayoutType>('force')
    const [use3D, setUse3D] = useState(false)
    const [isFullscreen, setIsFullscreen] = useState(false)
    const [includeDatabase, setIncludeDatabase] = useState(true)
    const [nodeLimit, setNodeLimit] = useState(NODE_STEP)
    const [zoom, setZoom] = useState(1)
    const [search, setSearch] = useState('')
    const [selectedNode, setSelectedNode] = useState<string | null>(null)
    const [positions, setPositions] = useState<Record<string, {x: number; y: number}>>({})

    const graphData = useMemo(() => {
        if (!graph || !includeDatabase) return {nodes: [], edges: []}
        const connections = new Map<string, number>()
        for (const edge of graph.edges) {
            connections.set(edge.source, (connections.get(edge.source) || 0) + 1)
            connections.set(edge.target, (connections.get(edge.target) || 0) + 1)
        }
        const sortedNodes = [...graph.nodes].sort((first, second) =>
            (connections.get(second.id) || 0) - (connections.get(first.id) || 0))
        const nodes = sortedNodes.slice(0, nodeLimit).map(node => ({
            ...node,
            connections: connections.get(node.id) || 0,
        }))
        const ids = new Set(nodes.map(node => node.id))
        return {nodes, edges: graph.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target))}
    }, [graph, includeDatabase, nodeLimit])

    useEffect(() => {
        const nodes: PositionedNode[] = graphData.nodes.map((node, index) => ({
            ...node,
            x: VIEW_WIDTH / 2 + Math.cos(index) * 100,
            y: VIEW_HEIGHT / 2 + Math.sin(index) * 100,
        }))
        if (!nodes.length) {
            setPositions({})
            return
        }
        if (layout === 'hierarchical') {
            const columns = Math.max(1, Math.ceil(Math.sqrt(nodes.length)))
            setPositions(Object.fromEntries(nodes.map((node, index) => [node.id, {
                x: 90 + (index % columns) * (720 / Math.max(1, columns - 1)),
                y: 80 + Math.floor(index / columns) * 105,
            }])))
            return
        }
        if (layout === 'radial') {
            const radius = Math.min(205, 95 + nodes.length * 4)
            setPositions(Object.fromEntries(nodes.map((node, index) => [node.id, {
                x: VIEW_WIDTH / 2 + Math.cos(index / nodes.length * Math.PI * 2 - Math.PI / 2) * radius,
                y: VIEW_HEIGHT / 2 + Math.sin(index / nodes.length * Math.PI * 2 - Math.PI / 2) * radius,
            }])))
            return
        }
        const links: PositionedLink[] = graphData.edges.map(edge => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            predicate: edge.predicate,
        }))
        const simulation = forceSimulation(nodes)
            .force('link', forceLink<PositionedNode, PositionedLink>(links).id(node => node.id).distance(92).strength(.6))
            .force('charge', forceManyBody().strength(-240))
            .force('center', forceCenter(VIEW_WIDTH / 2, VIEW_HEIGHT / 2))
            .force('collision', forceCollide<PositionedNode>().radius(node => 14 + Math.min(12, node.connections * 2)))
            .alphaDecay(.055)
            .on('tick', () => setPositions(Object.fromEntries(nodes.map(node => [node.id, {
                x: Math.max(35, Math.min(VIEW_WIDTH - 35, node.x || 0)),
                y: Math.max(35, Math.min(VIEW_HEIGHT - 35, node.y || 0)),
            }]))))
        return () => {
            simulation.stop()
        }
    }, [graphData, layout])

    useEffect(() => {
        const onFullscreen = () => setIsFullscreen(document.fullscreenElement === panelRef.current)
        const onKeyDown = (event: KeyboardEvent) => {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
                event.preventDefault()
                searchRef.current?.focus()
            }
        }
        document.addEventListener('fullscreenchange', onFullscreen)
        window.addEventListener('keydown', onKeyDown)
        return () => {
            document.removeEventListener('fullscreenchange', onFullscreen)
            window.removeEventListener('keydown', onKeyDown)
        }
    }, [])

    const normalizedSearch = search.trim().toLocaleLowerCase()
    const matchedIds = useMemo(() => new Set(graphData.nodes
        .filter(node => normalizedSearch && node.label.toLocaleLowerCase().includes(normalizedSearch))
        .map(node => node.id)), [graphData.nodes, normalizedSearch])
    const positionLookup = new Map(graphData.nodes.map(node => [node.id, positions[node.id]]))
    const selectedConnections = selectedNode ? graphData.edges.filter(edge =>
        edge.source === selectedNode || edge.target === selectedNode).length : 0

    async function toggleFullscreen() {
        if (document.fullscreenElement) await document.exitFullscreen()
        else await panelRef.current?.requestFullscreen()
    }

    function exportGraph(format: 'json' | 'csv') {
        if (!graph) return
        if (format === 'json') {
            download('knowledge-graph.json', JSON.stringify(graph, null, 2), 'application/json')
            return
        }
        const rows = ['subject,predicate,object,filename,chunk_index']
        const labels = new Map(graph.nodes.map(node => [node.id, node.label]))
        for (const edge of graph.edges) {
            rows.push([labels.get(edge.source), edge.predicate, labels.get(edge.target), edge.filename, edge.chunk_index]
                .map(value => `"${String(value || '').replaceAll('"', '""')}"`).join(','))
        }
        download('knowledge-graph.csv', rows.join('\n'), 'text/csv;charset=utf-8')
    }

    if (loading) return <p className="graph-state">正在載入知識圖譜…</p>
    if (error) return <p className="error" role="alert">{error}</p>

    return <section className="graph-workbench" aria-labelledby="graph-title" ref={panelRef}>
        <div className="graph-workbench-heading">
            <div className="graph-title-icon"><Eye size={18} weight="bold"/></div>
            <div><h2 id="graph-title">知識圖譜視覺化</h2><p>探索文件實體之間的連結，並以不同方式檢視你的知識圖譜。</p></div>
        </div>
        <div className="graph-workbench-body">
            <div className="graph-toolbar" aria-label="圖譜控制列">
                <div className="graph-toolbar-group primary-actions">
                    <button className={use3D ? 'active' : ''} onClick={() => setUse3D(value => !value)}
                            aria-pressed={use3D}><Cube size={17}/>{use3D ? '2D' : '3D'}</button>
                    <button onClick={toggleFullscreen}>{isFullscreen ? <CornersIn size={17}/> : <CornersOut size={17}/>}<span>{isFullscreen ? '退出' : '全螢幕'}</span></button>
                </div>
                <div className="graph-toolbar-divider"/>
                <div className="graph-layout-controls"><span>佈局：</span>{([
                    ['force', '力導向'], ['hierarchical', '樹狀'], ['radial', '放射'],
                ] as const).map(([value, label]) => <button className={layout === value ? 'active' : ''}
                    onClick={() => setLayout(value)} key={value}>{label}</button>)}</div>
                <div className="graph-toolbar-divider"/>
                <label className="database-switch"><input type="checkbox" checked={includeDatabase}
                    onChange={event => setIncludeDatabase(event.target.checked)}/><span className="switch-track"/>
                    <Database size={15}/><span>DB ({graph?.edges.length || 0})</span></label>
                <div className="graph-stats"><span>{graph?.nodes.length || 0} 個實體</span><b>•</b><span>{graph?.edges.length || 0} 個關係</span></div>
                <label className="graph-search"><MagnifyingGlass size={17}/><input ref={searchRef} value={search}
                    onChange={event => setSearch(event.target.value)} placeholder="搜尋實體… (⌘K)"/></label>
                <details className="export-menu"><summary><DownloadSimple size={17}/>匯出</summary><div>
                    <button onClick={() => exportGraph('json')}>JSON</button><button onClick={() => exportGraph('csv')}>CSV</button>
                </div></details>
            </div>

            <div className={`graph-stage ${use3D ? 'graph-stage-3d' : ''}`}>
                {!graph?.edges.length || !includeDatabase ? <div className="graph-empty"><Eye size={38}/>
                    <strong>{includeDatabase ? '尚未建立知識關係' : '資料庫圖譜已暫時隱藏'}</strong>
                    <span>{includeDatabase ? '上載文件後，系統會使用 Ollama 自動抽取三元組。' : '重新開啟 DB 切換即可顯示。'}</span>
                </div> : <>
                    {graphData.nodes.length < graph.nodes.length && <div className="graph-limit-notice">顯示 {graphData.nodes.length} / {graph.nodes.length} 個實體
                        <button onClick={() => setNodeLimit(value => Math.min(graph.nodes.length, value + NODE_STEP))}>顯示更多</button></div>}
                    {selectedNode && <div className="selected-node-card"><strong>{graphData.nodes.find(node => node.id === selectedNode)?.label}</strong>
                        <span>{selectedConnections} 個連結</span><button onClick={() => setSelectedNode(null)}>清除選取</button></div>}
                    <svg viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} role="img" aria-label="互動知識圖譜">
                        <g transform={`translate(${VIEW_WIDTH * (1 - zoom) / 2} ${VIEW_HEIGHT * (1 - zoom) / 2}) scale(${zoom})`}>
                            {graphData.edges.map(edge => {
                                const source = positionLookup.get(edge.source)
                                const target = positionLookup.get(edge.target)
                                if (!source || !target) return null
                                const connected = selectedNode && (edge.source === selectedNode || edge.target === selectedNode)
                                return <g className={`workbench-edge ${connected ? 'selected' : ''}`} key={edge.id}>
                                    <line x1={source.x} y1={source.y} x2={target.x} y2={target.y}/>
                                    {(connected || matchedIds.has(edge.source) || matchedIds.has(edge.target)) && <text
                                        x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 5}>{edge.predicate.slice(0, 18)}</text>}
                                </g>
                            })}
                            {graphData.nodes.map(node => {
                                const position = positionLookup.get(node.id)
                                if (!position) return null
                                const selected = selectedNode === node.id
                                const matched = matchedIds.has(node.id)
                                const radius = 7 + Math.min(7, node.connections * 1.4)
                                return <g className={`workbench-node ${selected ? 'selected' : ''} ${matched ? 'matched' : ''}`}
                                          key={node.id} transform={`translate(${position.x} ${position.y})`}
                                          onClick={() => setSelectedNode(node.id)} role="button" tabIndex={0}
                                          onKeyDown={event => event.key === 'Enter' && setSelectedNode(node.id)}>
                                    <circle r={radius}/>{(node.connections > 1 || selected || matched) && <text y={radius + 16}>{node.label.length > 24 ? `${node.label.slice(0, 23)}…` : node.label}</text>}
                                    <title>{node.label} · {node.connections} 個連結</title></g>
                            })}
                        </g>
                    </svg>
                    <div className="graph-stage-caption">{layout === 'force' ? '力導向圖譜' : layout === 'hierarchical' ? '樹狀圖譜' : '放射圖譜'}</div>
                    <div className="graph-zoom-controls"><button onClick={() => setZoom(value => Math.max(.6, value - .15))} aria-label="縮小"><Minus size={14}/></button>
                        <span>{Math.round(zoom * 100)}%</span><button onClick={() => setZoom(value => Math.min(1.8, value + .15))} aria-label="放大"><Plus size={14}/></button></div>
                </>}
            </div>
        </div>
    </section>
}
