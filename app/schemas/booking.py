from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.court import CourtPublic
from app.schemas.sport import SportPublic
from app.schemas.timeslot import TimeSlotPublic
from app.schemas.venue import VenuePublic


class BookingCreate(BaseModel):
    timeslot_id: UUID


class BookingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    timeslot_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class BookingPolicyPublic(BaseModel):
    min_booking_lead_minutes: int
    cancellation_min_lead_minutes: int
    booking_message: str
    cancellation_message: str


class CourtBookingPublic(CourtPublic):
    venue: VenuePublic
    sport: SportPublic


class TimeSlotBookingPublic(TimeSlotPublic):
    court: CourtBookingPublic


class BookingDetailPublic(BookingPublic):
    timeslot: TimeSlotBookingPublic
    can_cancel: bool = False
    cancellation_deadline: datetime | None = None
    cancellation_policy_message: str | None = None
