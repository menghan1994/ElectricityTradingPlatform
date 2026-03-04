from decouple import config


class Settings:
    # PostgreSQL
    POSTGRES_HOST: str = config("POSTGRES_HOST", default="postgresql")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432, cast=int)
    POSTGRES_DB: str = config("POSTGRES_DB", default="electricity_trading")
    POSTGRES_USER: str = config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="changeme")

    # api-server 专用数据库角色（生产环境使用 app_user 实现权限隔离）
    APP_DB_USER: str = config("APP_DB_USER", default="")
    APP_DB_PASSWORD: str = config("APP_DB_PASSWORD", default="")

    @property
    def DATABASE_URL(self) -> str:
        user = self.APP_DB_USER or self.POSTGRES_USER
        password = self.APP_DB_PASSWORD or self.POSTGRES_PASSWORD
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = config("REDIS_URL", default="redis://redis:6379/0")

    # JWT
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY", default="changeme-use-strong-secret")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = config("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", default=30, cast=int)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = config("JWT_REFRESH_TOKEN_EXPIRE_DAYS", default=7, cast=int)

    # LLM
    LLM_BASE_URL: str = config("LLM_BASE_URL", default="http://ollama:11434/v1")
    LLM_MODEL: str = config("LLM_MODEL", default="qwen3:8b")
    LLM_API_KEY: str = config("LLM_API_KEY", default="")

    # Langfuse
    LANGFUSE_HOST: str = config("LANGFUSE_HOST", default="http://langfuse:3000")
    LANGFUSE_PUBLIC_KEY: str = config("LANGFUSE_PUBLIC_KEY", default="")
    LANGFUSE_SECRET_KEY: str = config("LANGFUSE_SECRET_KEY", default="")

    # Celery
    CELERY_BROKER_URL: str = config("CELERY_BROKER_URL", default="redis://redis:6379/1")
    CELERY_RESULT_BACKEND: str = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")

    # Data Import
    DATA_IMPORT_DIR: str = config("DATA_IMPORT_DIR", default="./data/imports")
    MAX_IMPORT_FILE_SIZE: int = config("MAX_IMPORT_FILE_SIZE", default=104857600, cast=int)  # 100MB

    # Market Data
    MARKET_DATA_FETCH_TIMEOUT: int = config("MARKET_DATA_FETCH_TIMEOUT", default=30, cast=int)
    MARKET_DATA_DEFAULT_CACHE_TTL: int = config("MARKET_DATA_DEFAULT_CACHE_TTL", default=3600, cast=int)
    MARKET_DATA_RETRY_COUNT: int = config("MARKET_DATA_RETRY_COUNT", default=2, cast=int)
    MARKET_DATA_RETRY_BACKOFF: float = config("MARKET_DATA_RETRY_BACKOFF", default=1.0, cast=float)
    MARKET_DATA_ENCRYPTION_KEY: str = config("MARKET_DATA_ENCRYPTION_KEY", default="changeme-use-32-byte-key-here!!")

    # App
    APP_ENV: str = config("APP_ENV", default="development")
    APP_DEBUG: bool = config("APP_DEBUG", default=True, cast=bool)
    APP_LOG_LEVEL: str = config("APP_LOG_LEVEL", default="DEBUG")
    CORS_ORIGINS: list[str] = config(
        "CORS_ORIGINS",
        default="http://localhost:80,http://localhost:5173",
        cast=lambda v: [s.strip() for s in v.split(",")],
    )


settings = Settings()
