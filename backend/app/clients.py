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


async def chunk(base_url: str, text: str) -> list[dict]:
    data = await post_json(f"{base_url.rstrip('/')}/chunk", {"text": text})
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
