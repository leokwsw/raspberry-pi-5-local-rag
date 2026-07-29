import argparse
import asyncio
import time
from pathlib import Path

import psutil

from local_rag.benchmark import BenchmarkResult
from local_rag.generation import OllamaGenerator, OpenAICompatibleGenerator


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("llamacpp", "ollama"), default="llamacpp")
    parser.add_argument("--url", required=True)
    parser.add_argument("--model", default="")
    parser.add_argument("--prompt", default="Reply with one short sentence.")
    args = parser.parse_args()
    generator = (
        OllamaGenerator(args.url, args.model)
        if args.backend == "ollama"
        else OpenAICompatibleGenerator(args.url, args.model)
    )
    started = time.perf_counter()
    answer = await generator.generate(args.prompt)
    result = BenchmarkResult.measure(
        "llm",
        started,
        {"backend": args.backend, "model": args.model, "characters": len(answer),
         "process_rss": psutil.Process().memory_info().rss},
    )
    result.write(Path(f"benchmark/results/llm/{result.id}.json"))
    print(result.status)


if __name__ == "__main__":
    asyncio.run(main())
