import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:3b"
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash"
    DATABASE_URL: str = "sqlite+aiosqlite:///./taskforge.db"
    CORS_ORIGINS: str = "http://localhost:8501"
    API_KEY: str | None = None
    LOG_LEVEL: str = "INFO"

# Instantiate global settings
settings = Settings()

# Configure basic logging based on settings
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("taskforge")
