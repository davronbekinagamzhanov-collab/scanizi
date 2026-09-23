"""ScanIZI — Core configuration loaded from .env"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://scanizi_user:scanizi_pass_2024@localhost:5432/scanizi"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://scanizi_user:scanizi_pass_2024@localhost:5432/scanizi"

    # JWT
    JWT_SECRET: str = "scanizi-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    # Environment
    ENVIRONMENT: str = "development"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
