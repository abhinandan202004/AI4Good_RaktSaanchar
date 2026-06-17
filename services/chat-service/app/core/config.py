from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "RaktSaanchar Chat Service"
    APP_VERSION: str = "2.0.0"

    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379"
    RABBITMQ_URL: str = "amqp://rakt:rakt@rabbitmq/"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"

    NTFY_BASE_URL: str = "https://ntfy.sh"
    NTFY_TOPIC_PREFIX: str = "raktsaanchar"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
