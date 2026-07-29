import pytest

from local_rag.extraction import KnowledgeExtractor, normalize_entity


class JsonGenerator:
    async def generate(self, prompt: str) -> str:
        return '[{"subject":" Pi 5 ","predicate":"USES","object":" ARM ","confidence":0.9}]'

    async def stream(self, prompt: str):  # type: ignore[no-untyped-def]
        yield prompt


@pytest.mark.asyncio
async def test_extract_validates_normalizes_and_provenance() -> None:
    triples = await KnowledgeExtractor(JsonGenerator()).extract("chunk-1", "Pi 5 uses ARM")
    assert triples[0].subject == "pi 5"
    assert triples[0].chunk_id == "chunk-1"
    assert normalize_entity("  ARM ") == "arm"
