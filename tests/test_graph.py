from app.graph import KnowledgeGraphStore


def test_graph_store_replaces_and_deletes_document(tmp_path):
    store = KnowledgeGraphStore(str(tmp_path / "graph.db"))
    count = store.replace_document("doc-1", "notes.md", [
        {"subject": "Raspberry Pi 5", "predicate": "has", "object": "16GB RAM", "chunk_index": 2},
        {"subject": "Raspberry Pi 5", "predicate": "runs", "object": "Ollama", "chunk_index": 3},
    ])

    graph = store.graph()
    assert count == 2
    assert {node["label"] for node in graph["nodes"]} == {"Raspberry Pi 5", "16GB RAM", "Ollama"}
    assert len(graph["edges"]) == 2
    assert store.document_counts() == {"doc-1": 2}

    store.delete_document("doc-1")
    assert store.graph() == {"nodes": [], "edges": []}


def test_graph_store_deduplicates_same_relationship(tmp_path):
    store = KnowledgeGraphStore(str(tmp_path / "graph.db"))
    triple = {"subject": "Pi", "predicate": "uses", "object": "ARM64", "chunk_index": 1}

    assert store.replace_document("doc-1", "notes.md", [triple, triple]) == 1
