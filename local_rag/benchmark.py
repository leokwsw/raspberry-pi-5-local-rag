import json
import platform
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import psutil


def cpu_temperature() -> Optional[float]:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    if not path.exists():
        return None
    return int(path.read_text().strip()) / 1000


@dataclass(frozen=True)
class BenchmarkResult:
    id: str
    kind: str
    status: str
    duration_seconds: float
    metrics: dict[str, Any]
    environment: dict[str, Any]

    @classmethod
    def measure(cls, kind: str, started: float, metrics: dict[str, Any]) -> "BenchmarkResult":
        return cls(
            id=str(uuid.uuid4()),
            kind=kind,
            status="pending-device-validation",
            duration_seconds=time.perf_counter() - started,
            metrics=metrics,
            environment={
                "platform": platform.platform(),
                "machine": platform.machine(),
                "cpu_count": psutil.cpu_count(),
                "temperature_c": cpu_temperature(),
                "git_commit": _git_commit(),
            },
        )

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "unknown"
