from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.timeslot import TimeSlotPublic


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
    sport_id: UUID | None = None
    sport_name: str | None = None
    uses_default_policy: bool = True
    min_booking_lead_minutes: int
    cancellation_min_lead_minutes: int
    booking_message: str
    cancellation_message: str
    admin_summary: str


class VenueNestedPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None = None
    timezone: str
    allowed_sport_id: UUID | None = None


class SportNestedPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    booking_min_lead_minutes: int | None = None
    cancellation_min_lead_minutes: int | None = None


class CourtNestedPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    venue_id: UUID
    sport_id: UUID
    name: str
    indoor: bool | None = None
    is_active: bool
    venue: VenueNestedPublic
    sport: SportNestedPublic


class TimeSlotDetailPublic(TimeSlotPublic):
    court: CourtNestedPublic


class BookingDetailPublic(BookingPublic):
    can_cancel: bool = False
    cancellation_deadline: datetime | None = None
    cancellation_policy_message: str | None = None
    booking_policy_summary: str | None = None
    timeslot: TimeSlotDetailPublic
