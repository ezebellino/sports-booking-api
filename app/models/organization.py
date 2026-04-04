import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(150), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    users = relationship("User", back_populates="organization")
    venues = relationship("Venue", back_populates="organization")
    courts = relationship("Court", back_populates="organization")
    timeslots = relationship("TimeSlot", back_populates="organization")
    bookings = relationship("Booking", back_populates="organization")
    settings = relationship("OrganizationSettings", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    staff_invitations = relationship("StaffInvitation", back_populates="organization", cascade="all, delete-orphan")
    organization_sports = relationship("OrganizationSport", back_populates="organization", cascade="all, delete-orphan")
