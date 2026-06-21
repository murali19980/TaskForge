import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:3b"
    OLLAMA_MAX_CONCURRENT: int = 2
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash:free"
    OPENROUTER_MAX_CONCURRENT: int = 10
    DATABASE_URL: str = "sqlite+aiosqlite:///./taskforge.db"
    CORS_ORIGINS: str = "http://localhost:8501"
    API_KEY: str | None = None
    LOG_LEVEL: str = "INFO"
    MAX_INPUT_LENGTH: int = 2000
    MAX_COST_PER_REQUEST: float = 0.01

    @field_validator("OPENROUTER_MODEL")
    @classmethod
    def validate_openrouter_model(cls, v: str) -> str:
        if v and not (v.endswith(":free") or v == "openrouter/free"):
            raise ValueError(
                f"OPENROUTER_MODEL '{v}' is invalid. Only free models are allowed. "
                "Valid options must end with ':free' (e.g. 'google/gemini-2.5-flash:free') "
                "or be 'openrouter/free' (Free Models Router)."
            )
        return v

# Instantiate global settings
settings = Settings()

# Configure basic logging based on settings
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("taskforge")
