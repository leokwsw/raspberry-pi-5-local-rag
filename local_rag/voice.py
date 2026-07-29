import asyncio
import shutil
import wave
from pathlib import Path
from typing import Any


class VoiceService:
    def __init__(
        self, whisper_command: str, whisper_model: Path, piper_command: str, piper_model: Path
    ) -> None:
        self.whisper_command = whisper_command
        self.whisper_model = whisper_model
        self.piper_command = piper_command
        self.piper_model = piper_model

    def capabilities(self) -> dict[str, Any]:
        return {
            "stt": bool(shutil.which(self.whisper_command) and self.whisper_model.exists()),
            "tts": bool(shutil.which(self.piper_command) and self.piper_model.exists()),
        }

    @staticmethod
    def has_speech(path: Path, threshold: int = 300) -> bool:
        with wave.open(str(path), "rb") as audio:
            frames = audio.readframes(min(audio.getnframes(), audio.getframerate() * 3))
            width = audio.getsampwidth()
        if width != 2 or not frames:
            return False
        samples = [int.from_bytes(frames[i : i + 2], "little", signed=True)
                   for i in range(0, len(frames) - 1, 2)]
        return sum(abs(value) for value in samples) / len(samples) >= threshold

    async def transcribe(self, input_path: Path) -> str:
        if not self.capabilities()["stt"]:
            raise RuntimeError("stt_unavailable")
        process = await asyncio.create_subprocess_exec(
            self.whisper_command, "-m", str(self.whisper_model), "-f", str(input_path),
            "--output-txt", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, error = await process.communicate()
        if process.returncode:
            raise RuntimeError(error.decode(errors="replace"))
        output = input_path.with_suffix(input_path.suffix + ".txt")
        return output.read_text().strip()

    async def synthesize(self, text: str, output_path: Path) -> Path:
        if not self.capabilities()["tts"]:
            raise RuntimeError("tts_unavailable")
        process = await asyncio.create_subprocess_exec(
            self.piper_command, "--model", str(self.piper_model), "--output_file",
            str(output_path), stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, error = await process.communicate(text.encode())
        if process.returncode:
            raise RuntimeError(error.decode(errors="replace"))
        return output_path
