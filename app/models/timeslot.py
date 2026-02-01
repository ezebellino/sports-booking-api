from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Integer, Numeric, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base

class TimeSlot(Base):
    __tablename__ = "timeslots"
    __table_args__ = (
        UniqueConstraint("court_id", "starts_at", "ends_at", name="uq_timeslots_court_start_end"),
        CheckConstraint("ends_at > starts_at", name="ck_timeslots_end_after_start"),
        CheckConstraint("capacity > 0", name="ck_timeslots_capacity_positive"),
        Index("ix_timeslots_court_start", "court_id", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    court_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courts.id", ondelete="CASCADE"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    price: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    court = relationship("Court", back_populates="timeslots")
    bookings = relationship("Booking", back_populates="timeslot", cascade="all, delete-orphan")
