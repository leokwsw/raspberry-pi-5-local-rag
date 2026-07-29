import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from local_rag.generation import Generator


class TriplePayload(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=100)
    object: str = Field(min_length=1, max_length=200)
    confidence: float = Field(default=1.0, ge=0, le=1)


@dataclass(frozen=True)
class Triple:
    subject: str
    predicate: str
    object: str
    confidence: float
    chunk_id: str
    source_text: str


def normalize_entity(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


class KnowledgeExtractor:
    def __init__(self, generator: Generator, retries: int = 2) -> None:
        self.generator, self.retries = generator, retries

    async def extract(self, chunk_id: str, text: str) -> list[Triple]:
        prompt = (
            "Return only a JSON array of subject/predicate/object/confidence triples. "
            f"Text: {text}"
        )
        last_error: Exception = ValueError("empty response")
        for _ in range(self.retries + 1):
            try:
                payload = json.loads(await self.generator.generate(prompt))
                validated = [TriplePayload.model_validate(item) for item in payload]
                unique: dict[tuple[str, str, str], Triple] = {}
                for item in validated:
                    key = (
                        normalize_entity(item.subject),
                        normalize_entity(item.predicate),
                        normalize_entity(item.object),
                    )
                    unique[key] = Triple(*key, item.confidence, chunk_id, text)
                return list(unique.values())
            except (json.JSONDecodeError, ValidationError, TypeError) as error:
                last_error = error
        raise ValueError("knowledge extraction produced invalid JSON") from last_error
