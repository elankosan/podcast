"""Application configuration."""

import logging
import os
from typing import List, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/podcast"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_AUTH: str = "neo4j/podcast_password"

    # Kimi LLM
    KIMI_API_KEY: Optional[str] = None
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "kimi-k2-0711"

    # Auth
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # MAF
    MAF_WORKFORCE_PATH: str = "workforce.yaml"
    RUNTIME_LOGS_DIR: str = "/tmp/runtime_logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @model_validator(mode="after")
    def validate_secret_key(self):
        if not self.SECRET_KEY:
            self.SECRET_KEY = os.urandom(32).hex()
            logger.warning(
                "SECRET_KEY not set in environment. Using a random value. "
                "Set SECRET_KEY in your environment for production!"
            )
        return self

    def get_allowed_origins(self) -> List[str]:
        """Return parsed ALLOWED_ORIGINS as a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
