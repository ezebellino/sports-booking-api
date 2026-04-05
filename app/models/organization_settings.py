from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    organization_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    branding_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    booking_min_lead_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancellation_min_lead_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    whatsapp_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    whatsapp_access_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    whatsapp_template_language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_template_booking_confirmed: Mapped[str | None] = mapped_column(String(150), nullable=True)
    whatsapp_template_booking_cancelled: Mapped[str | None] = mapped_column(String(150), nullable=True)
    whatsapp_recipient_override: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organization = relationship("Organization", back_populates="settings")
