from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("user_id", "timeslot_id", name="uq_bookings_user_timeslot"),
        Index("ix_bookings_timeslot", "timeslot_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    timeslot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("timeslots.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="confirmed")  # confirmed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    timeslot = relationship("TimeSlot", back_populates="bookings")
    user = relationship("User", back_populates="bookings")