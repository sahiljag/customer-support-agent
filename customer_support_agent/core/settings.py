from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Copilot for Customer Support"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    llama_temperature: float = 0.2

    workspace_dir: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = Path("data")
    db_path: Path = Path("data/support.db")

    chroma_rag_dir: Path = Path("data/chroma_rag")
    chroma_mem0_dir: Path = Path("data/chroma_mem0")
    knowledge_base_dir: Path = Path("knowledge_base")

    rag_chunk_size: int = 300
    rag_chunk_overlap: int = 100
    rag_top_k: int = 2
    mem0_top_k: int = 5

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    dashboard_api_url: str = "http://localhost:8000"

    def resolve(self, path: Path) -> Path:
        return path if path.is_absolute() else self.workspace_dir / path

    @property
    def db_file(self) -> Path:
        return self.resolve(self.db_path)

    @property
    def chroma_rag_path(self) -> Path:
        return self.resolve(self.chroma_rag_dir)

    @property
    def chroma_mem0_path(self) -> Path:
        return self.resolve(self.chroma_mem0_dir)

    @property
    def knowledge_base_path(self) -> Path:
        return self.resolve(self.knowledge_base_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_directories(settings: Settings | None = None) -> None:
    """Create local directories required by sqlite and chromadb."""

    config = settings or get_settings()

    for path in (
        config.resolve(config.data_dir),
        config.chroma_rag_path,
        config.chroma_mem0_path,
        config.knowledge_base_path,
    ):
        path.mkdir(parents=True, exist_ok=True)