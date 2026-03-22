from pathlib import Path
from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"
# Load .env into os.environ so pydantic-settings picks it up reliably on Python 3.14
load_dotenv(_ENV_FILE, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Device — set all via .env
    device_id: str = ""
    device_ip: str = ""
    device_key: str = ""
    device_version: float = 3.5

    # AI
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-4-5-20251001"
    experiment_interval_minutes: int = 7

    # Location (for weather)
    weather_lat: float = 0.0
    weather_lon: float = 0.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
