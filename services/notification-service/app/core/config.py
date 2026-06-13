from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "RaktSaanchar Notification Service"
    APP_VERSION: str = "2.0.0"

    # Own DB (notifications schema)
    DATABASE_URL: str

    # Read-only access to core schema for user/donor/request lookups
    CORE_DB_URL: str = ""

    RABBITMQ_URL: str = "amqp://rakt:rakt@rabbitmq/"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"

    # SMTP (Gmail)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SENDER_NAME: str = "RaktSaanchar"

    # ntfy.sh push
    NTFY_BASE_URL: str = "https://ntfy.sh"
    NTFY_TOPIC_PREFIX: str = "raktsaanchar"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
