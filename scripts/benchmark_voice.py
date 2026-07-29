import argparse
import time
from pathlib import Path

from local_rag.benchmark import BenchmarkResult
from local_rag.config import Settings
from local_rag.voice import VoiceService

parser = argparse.ArgumentParser()
parser.add_argument("wav", type=Path)
args = parser.parse_args()
settings = Settings()
voice = VoiceService(
    settings.whisper_command, settings.whisper_model, settings.piper_command, settings.piper_model
)
started = time.perf_counter()
duration = 0.0
with __import__("wave").open(str(args.wav)) as audio:
    duration = audio.getnframes() / audio.getframerate()
result = BenchmarkResult.measure(
    "voice",
    started,
    {"audio_seconds": duration, "has_speech": voice.has_speech(args.wav),
     "capabilities": voice.capabilities()},
)
result.write(Path(f"benchmark/results/voice/{result.id}.json"))
