from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RaktaSanchaar API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ML Service (Developer 1's service)
    ML_SERVICE_URL: str = "http://ml-service:8002"

    # Chatbot Service
    CHATBOT_SERVICE_URL: str = "http://chatbot:8001"

    # File uploads
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # AWS SNS Settings
    AWS_ACCESS_KEY_ID: str = "mock"
    AWS_SECRET_ACCESS_KEY: str = "mock"
    AWS_REGION: str = "us-east-1"
    AWS_SNS_TOPIC_ARN: str = ""
    AWS_SNS_ENABLED: bool = False
    AWS_SNS_BUDGET_LIMIT: float = 40.0
    AWS_SNS_ESTIMATED_COST_PER_SMS: float = 0.02
    AWS_SES_SENDER: str = "no-reply@raktsaanchar.org"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
