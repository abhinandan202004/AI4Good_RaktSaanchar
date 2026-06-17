from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "RaktSaanchar Core Service"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379"
    RABBITMQ_URL: str = "amqp://rakt:rakt@rabbitmq/"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ML_SERVICE_URL: str = "http://ml-service:8005"

    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
