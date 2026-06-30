"""
Media processor for handling text, audio, and video files.
Extracts text content for RAG indexing.
Designed for lightweight operation on Raspberry Pi 5.
"""

import mimetypes
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from storage import Document


@dataclass
class ProcessedMedia:
    text: str
    content_type: str  # "text", "audio", "video"
    metadata: dict


class MediaProcessor:
    """Process various media types and extract text for RAG."""

    SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".csv", ".json", ".xml", ".html"}
    SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
    SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

    def __init__(self, whisper_model: str = "base"):
        self.whisper_model = whisper_model
        self._whisper_available: Optional[bool] = None
        self._ffmpeg_available: Optional[bool] = None

    def _check_whisper(self) -> bool:
        if self._whisper_available is None:
            try:
                import whisper
                self._whisper_available = True
            except ImportError:
                self._whisper_available = False
        return self._whisper_available

    def _check_ffmpeg(self) -> bool:
        if self._ffmpeg_available is None:
            try:
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    timeout=10,
                )
                self._ffmpeg_available = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._ffmpeg_available = False
        return self._ffmpeg_available

    def get_content_type(self, filepath: str) -> Optional[str]:
        ext = Path(filepath).suffix.lower()
        if ext in self.SUPPORTED_TEXT_EXTENSIONS:
            return "text"
        if ext in self.SUPPORTED_AUDIO_EXTENSIONS:
            return "audio"
        if ext in self.SUPPORTED_VIDEO_EXTENSIONS:
            return "video"
        return None

    def process_file(self, filepath: str) -> ProcessedMedia:
        """Process a file and extract text content."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        content_type = self.get_content_type(filepath)
        if content_type is None:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        if content_type == "text":
            return self._process_text(filepath)
        elif content_type == "audio":
            return self._process_audio(filepath)
        elif content_type == "video":
            return self._process_video(filepath)
        else:
            raise ValueError(f"Unknown content type: {content_type}")

    def _process_text(self, filepath: str) -> ProcessedMedia:
        """Process text files."""
        path = Path(filepath)
        ext = path.suffix.lower()

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(filepath, "r", encoding="latin-1") as f:
                text = f.read()

        text = self._clean_text(text)

        metadata = {
            "filename": path.name,
            "extension": ext,
            "size_bytes": path.stat().st_size,
            "char_count": len(text),
        }

        return ProcessedMedia(text=text, content_type="text", metadata=metadata)

    def _process_audio(self, filepath: str) -> ProcessedMedia:
        """Process audio files using Whisper for transcription."""
        path = Path(filepath)

        if not self._check_whisper():
            raise RuntimeError(
                "Whisper is not installed. Install with: pip install openai-whisper\n"
                "For Raspberry Pi, consider using whisper.cpp for better performance."
            )

        import whisper

        model = whisper.load_model(self.whisper_model)
        result = model.transcribe(filepath, language=None)
        text = result.get("text", "").strip()
        detected_language = result.get("language", "unknown")

        text = self._clean_text(text)

        metadata = {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "detected_language": detected_language,
            "transcription_model": self.whisper_model,
        }

        return ProcessedMedia(text=text, content_type="audio", metadata=metadata)

    def _process_video(self, filepath: str) -> ProcessedMedia:
        """Process video files by extracting audio and transcribing."""
        path = Path(filepath)

        if not self._check_ffmpeg():
            raise RuntimeError(
                "FFmpeg is not installed. Install with: sudo apt install ffmpeg"
            )

        if not self._check_whisper():
            raise RuntimeError(
                "Whisper is not installed. Install with: pip install openai-whisper"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_audio_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", filepath,
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",
                    "-ac", "1",
                    "-y",
                    tmp_audio_path,
                ],
                capture_output=True,
                timeout=300,
            )

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr.decode()}")

            import whisper
            model = whisper.load_model(self.whisper_model)
            transcribe_result = model.transcribe(tmp_audio_path, language=None)
            text = transcribe_result.get("text", "").strip()
            detected_language = transcribe_result.get("language", "unknown")

        finally:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)

        text = self._clean_text(text)

        metadata = {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "detected_language": detected_language,
            "transcription_model": self.whisper_model,
        }

        return ProcessedMedia(text=text, content_type="video", metadata=metadata)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def create_document(self, filepath: str) -> Document:
        """Process a file and create a Document object."""
        processed = self.process_file(filepath)
        path = Path(filepath)

        return Document(
            id=str(uuid.uuid4()),
            filename=path.name,
            content_type=processed.content_type,
            text_content=processed.text,
            source_path=str(path.absolute()),
            metadata=processed.metadata,
        )


class TextChunker:
    """Split text into chunks for embedding."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n\n",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []

        paragraphs = text.split(self.separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + len(self.separator) <= self.chunk_size:
                if current_chunk:
                    current_chunk += self.separator + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    overlap_text = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else ""
                    current_chunk = overlap_text + self.separator + para if overlap_text else para
                else:
                    if len(para) > self.chunk_size:
                        for i in range(0, len(para), self.chunk_size - self.chunk_overlap):
                            chunk = para[i:i + self.chunk_size]
                            if chunk:
                                chunks.append(chunk)
                        current_chunk = ""
                    else:
                        current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def chunk_document(self, doc: Document) -> list[dict]:
        """Chunk a document and return chunk dicts with metadata."""
        chunks = self.chunk_text(doc.text_content)
        result = []

        for i, chunk_text in enumerate(chunks):
            chunk_id = f"{doc.id}_chunk_{i}"
            result.append({
                "id": chunk_id,
                "text": chunk_text,
                "document_id": doc.id,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "metadata": {
                    "filename": doc.filename,
                    "content_type": doc.content_type,
                    **doc.metadata,
                },
            })

        return result


def get_supported_extensions() -> dict[str, list[str]]:
    """Return supported file extensions by type."""
    return {
        "text": list(MediaProcessor.SUPPORTED_TEXT_EXTENSIONS),
        "audio": list(MediaProcessor.SUPPORTED_AUDIO_EXTENSIONS),
        "video": list(MediaProcessor.SUPPORTED_VIDEO_EXTENSIONS),
    }
