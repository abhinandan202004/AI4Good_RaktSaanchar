from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "RaktSaanchar Chatbot Service"
    APP_VERSION: str = "2.0.0"

    REDIS_URL: str = "redis://redis:6379"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"

    # AI API Keys
    MISTRAL_API_KEY: str = ""
    SARVAM_API_KEY: str = ""

    # Core service URL for blood request data lookups
    CORE_SERVICE_URL: str = "http://core-service:8002"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8003"
    AUTH_SERVICE_URL: str = "http://auth-service:8001"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
