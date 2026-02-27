from decouple import config


class Settings:
    # LLM
    LLM_BASE_URL: str = config("LLM_BASE_URL", default="http://ollama:11434/v1")
    LLM_MODEL: str = config("LLM_MODEL", default="qwen3:8b")
    LLM_API_KEY: str = config("LLM_API_KEY", default="")

    # PostgreSQL (for langgraph checkpoint)
    POSTGRES_HOST: str = config("POSTGRES_HOST", default="postgresql")
    POSTGRES_PORT: int = config("POSTGRES_PORT", default=5432, cast=int)
    POSTGRES_DB: str = config("POSTGRES_DB", default="electricity_trading")
    POSTGRES_USER: str = config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = config("POSTGRES_PASSWORD", default="changeme")

    @property
    def CHECKPOINT_DB_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Langfuse
    LANGFUSE_HOST: str = config("LANGFUSE_HOST", default="http://langfuse:3000")
    LANGFUSE_PUBLIC_KEY: str = config("LANGFUSE_PUBLIC_KEY", default="")
    LANGFUSE_SECRET_KEY: str = config("LANGFUSE_SECRET_KEY", default="")

    # App
    APP_ENV: str = config("APP_ENV", default="development")
    APP_DEBUG: bool = config("APP_DEBUG", default=True, cast=bool)


settings = Settings()
