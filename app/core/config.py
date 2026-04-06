from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 7
    DATABASE_URL: str
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    BOOKING_MIN_LEAD_MINUTES: int = 30
    CANCELLATION_MIN_LEAD_MINUTES: int = 120
    WHATSAPP_PROVIDER: str = "disabled"
    WHATSAPP_API_VERSION: str = "v23.0"
    WHATSAPP_ACCESS_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_TEMPLATE_LANGUAGE: str = "es_AR"
    WHATSAPP_TEMPLATE_BOOKING_CONFIRMED: str = "booking_confirmation"
    WHATSAPP_TEMPLATE_BOOKING_CANCELLED: str = "booking_cancellation"
    WHATSAPP_RECIPIENT_OVERRIDE: str | None = None
    MEDIA_ROOT: str = "uploads"
    MEDIA_URL_PREFIX: str = "/media"
    MEDIA_STORAGE_BACKEND: str = "local"
    ORGANIZATION_LOGO_DIR: str = "organization-logos"
    MAX_LOGO_UPLOAD_BYTES: int = 2 * 1024 * 1024
    S3_BUCKET_NAME: str | None = None
    S3_REGION: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_PUBLIC_BASE_URL: str | None = None
    S3_KEY_PREFIX: str = ""
    FRONTEND_PUBLIC_URL: str = "http://localhost:5173"
    EMAIL_PROVIDER: str = "disabled"
    EMAIL_FROM: str | None = None
    EMAIL_FROM_NAME: str = "Sports Booking"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]

if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
