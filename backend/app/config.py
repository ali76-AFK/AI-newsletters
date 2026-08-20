from __future__ import annotations

import os

from pydantic import BaseModel, Field, ValidationError


class Settings(BaseModel):
    env: str = Field(default="development")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)

    db_host: str = Field(default="127.0.0.1")
    db_port: int = Field(default=55432)
    db_name: str = Field(default="newsletter")
    db_user: str = Field(default="newsletter_user")
    db_password: str = Field(default="newsletter_password")

    llm_provider: str = Field(default="mock")
    ollama_model: str = Field(default="llama3.1:8b")
    groq_api_key: str | None = Field(default=None)
    groq_model: str = Field(
        default="replace_with_supported_groq_model"
    )

    email_mode: str = Field(default="mock")
    news_source_mode: str = Field(default="stub")

    @property
    def sqlalchemy_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


def load_settings() -> Settings:
    try:
        return Settings(
            env=os.getenv("APP_ENV", "development"),
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8000")),
            db_host=os.getenv("DB_HOST", "127.0.0.1"),
            db_port=int(os.getenv("DB_PORT", "55432")),
            db_name=os.getenv("DB_NAME", "newsletter"),
            db_user=os.getenv("DB_USER", "newsletter_user"),
            db_password=os.getenv("DB_PASSWORD", "newsletter_password"),
            llm_provider=os.getenv("LLM_PROVIDER", "mock"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            groq_model=os.getenv(
                "GROQ_MODEL",
                "replace_with_supported_groq_model",
            ),
            email_mode=os.getenv("EMAIL_MODE", "mock"),
            news_source_mode=os.getenv(
                "NEWS_SOURCE_MODE",
                "stub",
            ),
        )
    except ValidationError as exc:
        raise RuntimeError(
            f"Invalid configuration: {exc}"
        ) from exc
