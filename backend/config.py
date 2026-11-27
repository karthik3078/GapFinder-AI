from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    ai_mode: Literal['demo', 'live'] = 'demo'
    embedding_provider: Literal['local', 'google'] = 'local'
    gemini_api_key: str = ''
    gemini_model: str = 'gemini-2.5-flash'
    embedding_model: str = 'gemini-embedding-001'
    embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    generation_temperature: float = Field(default=0.2, ge=0, le=1)
    model_timeout_seconds: int = Field(default=60, ge=5, le=180)
    retrieval_min_similarity: float = Field(default=0.12, ge=0, le=1)
    mapping_min_confidence: float = Field(default=0.22, ge=0, le=1)
    storage_dir: Path = ROOT / 'storage'
    allowed_origins: str = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000'
    cookie_secure: bool = False
    seed_demo_user: bool = True
    max_upload_mb: int = Field(default=10, ge=1, le=30)

    @model_validator(mode='after')
    def resolve(self):
        if not self.storage_dir.is_absolute():
            self.storage_dir = ROOT / self.storage_dir
        if (self.ai_mode == 'live' or self.embedding_provider == 'google') and not self.gemini_api_key:
            raise ValueError('GEMINI_API_KEY is required for live AI or Google embeddings. Use demo + local for offline use.')
        return self

    @property
    def origins(self):
        return [x.strip().rstrip('/') for x in self.allowed_origins.split(',') if x.strip()]
