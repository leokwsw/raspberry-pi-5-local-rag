import time
from pathlib import Path

import psutil

from local_rag.benchmark import BenchmarkResult

started = time.perf_counter()
result = BenchmarkResult.measure(
    "hardware",
    started,
    {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": dict(psutil.virtual_memory()._asdict()),
    },
)
result.write(Path("benchmark/results/hardware/latest.json"))
print(result.status)
