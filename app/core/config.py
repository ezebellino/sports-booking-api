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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
