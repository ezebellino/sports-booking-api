from typing import Optional
from sqlalchemy import String, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class Court(Base):
    __tablename__ = "courts"
    __table_args__ = (
        UniqueConstraint("venue_id", "name", name="uq_courts_venue_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id", ondelete="RESTRICT"), nullable=False, index=True)
    sport_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sports.id", ondelete="RESTRICT"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    indoor: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    venue = relationship("Venue", back_populates="courts")
    sport = relationship("Sport", back_populates="courts")
    timeslots = relationship("TimeSlot", back_populates="court", cascade="all, delete-orphan")
