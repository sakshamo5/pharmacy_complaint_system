from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_TITLE: str = "AIVOA Pharmacy Complaint System"
    APP_VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/pharmacy_complaints"

    # Groq LLM
    GROQ_API_KEY: str = ""
    # NOTE: The assignment-recommended gemma2-9b-it and llama-3.3-70b-versatile
    # have been decommissioned / removed on Groq (verified Sept 2026), so we
    # default to Groq's available OpenAI-preview family. Change via .env:
    #   PRIMARY_MODEL=...   FALLBACK_MODEL=...
    PRIMARY_MODEL: str = "openai/gpt-oss-20b"
    FALLBACK_MODEL: str = "openai/gpt-oss-120b"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".eml"]

    # Duplicate detection: max day difference between complaint dates to still count as a match
    DATE_TOLERANCE_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
