from uuid import uuid4

from qdrant_client import AsyncQdrantClient, models


class VectorStore:
    def __init__(self, url: str, collection: str) -> None:
        self.client = AsyncQdrantClient(url=url, timeout=60)
        self.collection = collection

    async def ensure_collection(self, vector_size: int) -> None:
        if not await self.client.collection_exists(self.collection):
            await self.client.create_collection(
                self.collection,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )

    async def add_document(self, document_id: str, filename: str, size: int, chunks: list[dict],
                           vectors: list[list[float]]) -> None:
        await self.ensure_collection(len(vectors[0]))
        points = [
            models.PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "document_id": document_id,
                    "filename": filename,
                    "size": size,
                    "chunk_index": item["index"],
                    "text": item["text"],
                    "chunk_count": len(chunks),
                },
            )
            for item, vector in zip(chunks, vectors, strict=True)
        ]
        await self.client.upsert(self.collection, points=points, wait=True)

    async def search(self, vector: list[float], limit: int) -> list[dict]:
        if not await self.client.collection_exists(self.collection):
            return []
        result = await self.client.query_points(self.collection, query=vector, limit=limit, with_payload=True)
        return [
            {"id": str(point.id), "score": float(point.score), **(point.payload or {})}
            for point in result.points
        ]

    async def list_documents(self) -> list[dict]:
        if not await self.client.collection_exists(self.collection):
            return []
        documents: dict[str, dict] = {}
        offset = None
        while True:
            points, offset = await self.client.scroll(self.collection, limit=256, offset=offset, with_payload=True,
                                                      with_vectors=False)
            for point in points:
                payload = point.payload or {}
                doc_id = str(payload.get("document_id", ""))
                if doc_id and doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": payload.get("filename", "unknown"),
                        "size": int(payload.get("size", 0)),
                        "chunk_count": int(payload.get("chunk_count", 0)),
                    }
            if offset is None:
                break
        return sorted(documents.values(), key=lambda item: item["filename"].lower())

    async def delete_document(self, document_id: str) -> None:
        if await self.client.collection_exists(self.collection):
            await self.client.delete(
                self.collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
                    )
                ),
                wait=True,
            )
