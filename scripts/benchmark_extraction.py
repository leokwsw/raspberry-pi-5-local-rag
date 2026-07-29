import asyncio
import time
from pathlib import Path

from local_rag.benchmark import BenchmarkResult
from local_rag.extraction import KnowledgeExtractor
from local_rag.generation import EchoGenerator


async def main() -> None:
    started = time.perf_counter()
    malformed = 0
    try:
        await KnowledgeExtractor(EchoGenerator()).extract("sample", "Sample text")
    except ValueError:
        malformed = 1
    result = BenchmarkResult.measure("knowledge-extraction", started, {"malformed": malformed})
    result.write(Path(f"benchmark/results/extraction/{result.id}.json"))


if __name__ == "__main__":
    asyncio.run(main())
