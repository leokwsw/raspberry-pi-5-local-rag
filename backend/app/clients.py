import json
import re
from collections.abc import Sequence

import httpx


class ServiceError(RuntimeError):
    pass


_THINK_BLOCK = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.IGNORECASE | re.DOTALL)
_THINK_END = re.compile(r"</think(?:ing)?>", re.IGNORECASE)


def strip_thinking_output(content: str) -> str:
    """Return only the user-facing answer if a model leaks its reasoning trace."""
    cleaned = _THINK_BLOCK.sub("", content)
    if _THINK_END.search(cleaned):
        cleaned = _THINK_END.split(cleaned)[-1]
    return cleaned.strip()


async def post_json(url: str, payload: dict, timeout: float = 120.0) -> dict:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ServiceError(f"服務請求失敗：{url}") from exc


async def embed(base_url: str, model: str, texts: Sequence[str]) -> list[list[float]]:
    data = await post_json(
        f"{base_url.rstrip('/')}/api/embed",
        {"model": model, "input": list(texts)},
    )
    embeddings = data.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise ServiceError("Ollama embedding 回應格式不正確")
    return embeddings


async def chunk(base_url: str, text: str, chunk_size: int | None = None,
                overlap: int | None = None) -> list[dict]:
    payload: dict = {"text": text}
    if chunk_size is not None:
        payload["chunk_size"] = chunk_size
    if overlap is not None:
        payload["overlap"] = overlap
    data = await post_json(f"{base_url.rstrip('/')}/chunk", payload)
    return data["chunks"]


async def rerank(base_url: str, query: str, documents: list[dict], top_n: int) -> list[dict]:
    data = await post_json(
        f"{base_url.rstrip('/')}/rerank",
        {"query": query, "documents": documents, "top_n": top_n},
    )
    return data.get("results", [])


async def generate(base_url: str, model: str, messages: list[dict]) -> str:
    data = await post_json(
        f"{base_url.rstrip('/')}/api/chat",
        {"model": model, "messages": messages, "stream": False, "think": False},
        timeout=300.0,
    )
    content = data.get("message", {}).get("content", "")
    return strip_thinking_output(content) if isinstance(content, str) else ""


def parse_triples(content: str, chunk_index: int, limit: int = 40) -> list[dict]:
    """Parse and validate a compact Ollama JSON triple response."""
    cleaned = strip_thinking_output(content).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        payload = json.loads(cleaned)
    except (TypeError, json.JSONDecodeError):
        return []
    raw_triples = payload.get("triples", []) if isinstance(payload, dict) else []
    if not isinstance(raw_triples, list):
        return []
    triples: list[dict] = []
    for item in raw_triples[:limit]:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject", "")).strip()[:200]
        predicate = str(item.get("predicate", "")).strip()[:200]
        object_value = str(item.get("object", "")).strip()[:200]
        if subject and predicate and object_value and subject.casefold() != object_value.casefold():
            triples.append({
                "subject": subject,
                "predicate": predicate,
                "object": object_value,
                "chunk_index": chunk_index,
            })
    return triples


async def extract_triples(base_url: str, model: str, text: str, chunk_index: int,
                          system_prompt: str | None = None) -> list[dict]:
    data = await post_json(
        f"{base_url.rstrip('/')}/api/chat",
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or (
                        "從內容抽取明確、可驗證的知識三元組。只輸出 JSON："
                        '{"triples":[{"subject":"實體","predicate":"關係","object":"實體或值"}]}。'
                        "不可加入內容沒有陳述的知識；沒有三元組時輸出空陣列。"
                    ),
                },
                {"role": "user", "content": f"內容：\n{text}\n\n/no_think"},
            ],
            "stream": False,
            "think": False,
            "format": "json",
        },
        timeout=300.0,
    )
    content = data.get("message", {}).get("content", "")
    return parse_triples(content, chunk_index) if isinstance(content, str) else []
