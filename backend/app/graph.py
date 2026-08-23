"""ArangoDB-backed persistence for document knowledge triples."""

import hashlib
import threading
from collections.abc import Iterable

from arango import ArangoClient


class KnowledgeGraphStore:
    vertex_collection = "knowledge_entities"
    edge_collection = "knowledge_relations"
    graph_name = "document_knowledge_graph"

    def __init__(self, url: str, database: str, username: str = "root", password: str = "") -> None:
        self.url = url
        self.database_name = database
        self.username = username
        self.password = password
        self._db = None
        self._lock = threading.Lock()

    def _database(self):
        if self._db is not None:
            return self._db
        with self._lock:
            if self._db is not None:
                return self._db
            client = ArangoClient(hosts=self.url)
            system_db = client.db("_system", username=self.username, password=self.password)
            if not system_db.has_database(self.database_name):
                system_db.create_database(self.database_name)
            database = client.db(self.database_name, username=self.username, password=self.password)
            graph = database.graph(self.graph_name) if database.has_graph(self.graph_name) \
                else database.create_graph(self.graph_name)
            if not graph.has_vertex_collection(self.vertex_collection):
                graph.create_vertex_collection(self.vertex_collection)
            if not graph.has_edge_definition(self.edge_collection):
                graph.create_edge_definition(
                    edge_collection=self.edge_collection,
                    from_vertex_collections=[self.vertex_collection],
                    to_vertex_collections=[self.vertex_collection],
                )
            self._db = database
            return database

    def replace_document(self, document_id: str, filename: str, triples: Iterable[dict]) -> int:
        database = self._database()
        self.delete_document(document_id)
        vertices = database.collection(self.vertex_collection)
        edges = database.collection(self.edge_collection)
        inserted_edges: set[str] = set()
        for item in triples:
            subject = self._clean(item.get("subject"))
            predicate = self._clean(item.get("predicate"))
            object_value = self._clean(item.get("object"))
            if not subject or not predicate or not object_value or subject.casefold() == object_value.casefold():
                continue
            subject_key = self._entity_key(subject)
            object_key = self._entity_key(object_value)
            vertices.insert({"_key": subject_key, "label": subject}, overwrite_mode="ignore")
            vertices.insert({"_key": object_key, "label": object_value}, overwrite_mode="ignore")
            edge_key = self._edge_key(document_id, subject, predicate, object_value)
            if edge_key in inserted_edges:
                continue
            edges.insert({
                "_key": edge_key,
                "_from": f"{self.vertex_collection}/{subject_key}",
                "_to": f"{self.vertex_collection}/{object_key}",
                "document_id": document_id,
                "filename": filename,
                "predicate": predicate,
                "chunk_index": int(item.get("chunk_index", 0)),
            }, overwrite_mode="ignore")
            inserted_edges.add(edge_key)
        return len(inserted_edges)

    def delete_document(self, document_id: str) -> None:
        database = self._database()
        database.aql.execute("""
            FOR edge IN @@edges
                FILTER edge.document_id == @document_id
                REMOVE edge IN @@edges
        """, bind_vars={"@edges": self.edge_collection, "document_id": document_id})
        database.aql.execute("""
            FOR vertex IN @@vertices
                LET references = LENGTH(
                    FOR edge IN @@edges
                        FILTER edge._from == vertex._id OR edge._to == vertex._id
                        LIMIT 1
                        RETURN 1
                )
                FILTER references == 0
                REMOVE vertex IN @@vertices
        """, bind_vars={"@vertices": self.vertex_collection, "@edges": self.edge_collection})

    def document_counts(self) -> dict[str, int]:
        database = self._database()
        cursor = database.aql.execute("""
            FOR edge IN @@edges
                COLLECT document_id = edge.document_id WITH COUNT INTO triple_count
                RETURN { document_id, triple_count }
        """, bind_vars={"@edges": self.edge_collection})
        return {str(item["document_id"]): int(item["triple_count"]) for item in cursor}

    def graph(self, document_id: str | None = None) -> dict:
        database = self._database()
        cursor = database.aql.execute("""
            FOR edge IN @@edges
                FILTER @document_id == null OR edge.document_id == @document_id
                LET source = DOCUMENT(edge._from)
                LET target = DOCUMENT(edge._to)
                SORT source.label, edge.predicate, target.label
                RETURN {
                    id: edge._key,
                    source_id: source._key,
                    source_label: source.label,
                    target_id: target._key,
                    target_label: target.label,
                    predicate: edge.predicate,
                    document_id: edge.document_id,
                    filename: edge.filename,
                    chunk_index: edge.chunk_index
                }
        """, bind_vars={"@edges": self.edge_collection, "document_id": document_id})
        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        for item in cursor:
            source_id = str(item["source_id"])
            target_id = str(item["target_id"])
            nodes.setdefault(source_id, {"id": source_id, "label": str(item["source_label"])})
            nodes.setdefault(target_id, {"id": target_id, "label": str(item["target_label"])})
            edges.append({
                "id": str(item["id"]),
                "source": source_id,
                "target": target_id,
                "predicate": str(item["predicate"]),
                "document_id": str(item["document_id"]),
                "filename": str(item["filename"]),
                "chunk_index": int(item["chunk_index"]),
            })
        return {"nodes": list(nodes.values()), "edges": edges}

    @staticmethod
    def _clean(value: object) -> str:
        return value.strip()[:200] if isinstance(value, str) else ""

    @staticmethod
    def _entity_key(label: str) -> str:
        normalized = " ".join(label.casefold().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _edge_key(document_id: str, subject: str, predicate: str, object_value: str) -> str:
        identity = "\x1f".join((document_id, subject.casefold(), predicate.casefold(), object_value.casefold()))
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
