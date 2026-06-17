from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "RaktSaanchar ML Service"
    APP_VERSION: str = "2.0.0"

    # Read-only access to core schema
    DATABASE_URL: str

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"

    # Model paths — mounted from host volume ./models:/app/models
    MODEL_PATH: str = "/app/models/donor_ranking_xgboost.pkl"
    COLS_PATH: str = "/app/models/feature_columns.pkl"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
