from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API Keys
    openai_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # Fallback (gdy Ollama zawiedzie – błąd połączenia, brak modelu, timeout)
    fallback_model: str = "gpt-4o-mini"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "notebook_notes"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Models
    whisper_model: str = "whisper-1"
    embedding_model: str = "text-embedding-3-small"
    embedding_size: int = 1536

    # Storage
    data_dir: Path = Path("data")

    @property
    def notes_file(self) -> Path:
        return self.data_dir / "notes.json"

    @property
    def calendar_file(self) -> Path:
        return self.data_dir / "calendar.json"


settings = Settings()
