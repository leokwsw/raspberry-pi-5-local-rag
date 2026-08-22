from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:4b"
    ollama_embed_model: str = "qwen3-embedding:0.6b"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "local_rag_chunks"
    chunking_url: str = "http://localhost:8082"
    reranker_url: str = "http://localhost:8081"
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 20
    retrieval_limit: int = 20
    rerank_limit: int = 5

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
