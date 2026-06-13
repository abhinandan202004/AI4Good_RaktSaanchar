from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "RaktSaanchar Auth Service"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Database (auth schema)
    DATABASE_URL: str

    # Redis (OTP + refresh token storage)
    REDIS_URL: str = "redis://redis:6379"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://rakt:rakt@rabbitmq/"

    # JWT (shared with ALL services — never change the secret without redeploying everything)
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SMTP (replaces AWS SES)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SENDER_NAME: str = "RaktSaanchar"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
