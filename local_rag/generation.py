from collections.abc import AsyncIterator
from typing import Protocol

import httpx


class Generator(Protocol):
    async def generate(self, prompt: str) -> str: ...

    async def stream(self, prompt: str) -> AsyncIterator[str]: ...


class OpenAICompatibleGenerator:
    def __init__(self, base_url: str, model: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)


class OllamaGenerator:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url, self.model = base_url.rstrip("/"), model

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return str(response.json()["response"])

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield await self.generate(prompt)


class EchoGenerator:
    """Deterministic offline adapter used by tests and degraded operation."""

    async def generate(self, prompt: str) -> str:
        return prompt

    async def stream(self, prompt: str) -> AsyncIterator[str]:
        yield prompt
