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

    async def overview(self) -> dict:
        if not await self.client.collection_exists(self.collection):
            return {"connected": True, "vector_count": 0}
        collection = await self.client.get_collection(self.collection)
        return {"connected": True, "vector_count": int(collection.points_count or 0)}

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

    async def search(self, vector: list[float], limit: int, document_ids: list[str] | None = None) -> list[dict]:
        if not await self.client.collection_exists(self.collection):
            return []
        query_filter = None
        if document_ids:
            query_filter = models.Filter(must=[
                models.FieldCondition(key="document_id", match=models.MatchAny(any=document_ids)),
            ])
        result = await self.client.query_points(
            self.collection, query=vector, query_filter=query_filter, limit=limit, with_payload=True,
        )
        return [
            {"id": str(point.id), "score": float(point.score), **(point.payload or {})}
            for point in result.points
        ]

    async def all_chunks(self, document_ids: list[str] | None = None) -> list[dict]:
        if not await self.client.collection_exists(self.collection):
            return []
        chunks: list[dict] = []
        offset = None
        while True:
            scroll_filter = None
            if document_ids:
                scroll_filter = models.Filter(must=[
                    models.FieldCondition(key="document_id", match=models.MatchAny(any=document_ids)),
                ])
            points, offset = await self.client.scroll(
                self.collection, limit=256, offset=offset, scroll_filter=scroll_filter,
                with_payload=True, with_vectors=False,
            )
            chunks.extend({"id": str(point.id), **(point.payload or {})} for point in points)
            if offset is None:
                return chunks

    async def neighbors(self, document_id: str, chunk_index: int, window: int) -> list[dict]:
        if not await self.client.collection_exists(self.collection) or window <= 0:
            return []
        points, _ = await self.client.scroll(
            self.collection,
            limit=window * 2 + 1,
            with_payload=True,
            with_vectors=False,
            scroll_filter=models.Filter(must=[
                models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
                models.FieldCondition(
                    key="chunk_index",
                    range=models.Range(gte=max(0, chunk_index - window), lte=chunk_index + window),
                ),
            ]),
        )
        return sorted(
            [{"id": str(point.id), **(point.payload or {})} for point in points],
            key=lambda item: int(item.get("chunk_index", 0)),
        )

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
