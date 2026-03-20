from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Vapi
    vapi_api_key: str = ""
    vapi_assistant_id: str = ""
    voice_agent_webhook_url: str = ""
    vapi_webhook_secret: str = ""

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    

# settings = Settings()
@lru_cache
def get_settings() -> Settings:
    return Settings()