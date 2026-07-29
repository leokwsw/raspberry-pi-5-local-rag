from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAG_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    database_path: Path = Path("data/rag.db")
    llm_backend: str = "llamacpp"
    llamacpp_url: str = "http://127.0.0.1:8080"
    ollama_url: str = "http://127.0.0.1:11434"
    model_name: str = ""
    chunk_size: int = 800
    chunk_overlap: int = 120
    enable_kg: bool = False
    enable_graphrag: bool = False
    enable_voice: bool = False
    whisper_command: str = "whisper-cli"
    whisper_model: Path = Path("models/stt/model.bin")
    piper_command: str = "piper"
    piper_model: Path = Path("models/tts/voice.onnx")

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
