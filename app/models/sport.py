from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.db.base import Base


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    booking_min_lead_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cancellation_min_lead_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    courts = relationship("Court", back_populates="sport", cascade="all, delete-orphan")
