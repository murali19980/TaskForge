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
    OPENROUTER_MODELS: str = ""
    OPENROUTER_MAX_CONCURRENT: int = 10
    DATABASE_URL: str = "sqlite+aiosqlite:///./taskforge.db"
    CORS_ORIGINS: str = ""
    API_KEY: str | None = None
    LOG_LEVEL: str = "INFO"
    MAX_INPUT_LENGTH: int = 2000
    MAX_COST_PER_REQUEST: float = 0.01
    LLM_REQUEST_TIMEOUT: int = 120
    RATE_LIMIT_PER_MINUTE: int = 5

    @property
    def openrouter_model_list(self) -> list[str]:
        if self.OPENROUTER_MODELS:
            return [m.strip() for m in self.OPENROUTER_MODELS.split(",") if m.strip()]
        return [self.OPENROUTER_MODEL] if self.OPENROUTER_MODEL else []

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

    @field_validator("OPENROUTER_MODELS")
    @classmethod
    def validate_openrouter_models(cls, v: str) -> str:
        if v:
            models = [m.strip() for m in v.split(",") if m.strip()]
            for m in models:
                if not (m.endswith(":free") or m == "openrouter/free"):
                    raise ValueError(
                        f"Model '{m}' in OPENROUTER_MODELS is invalid. Only free models are allowed. "
                        "Valid options must end with ':free' or be 'openrouter/free'."
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
