from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from uuid import UUID

class TimeSlotCreate(BaseModel):
    court_id: UUID
    starts_at: datetime
    ends_at: datetime
    capacity: int = 1
    price: int | None = None
    is_active: bool = True

    @field_validator("ends_at")
    @classmethod
    def end_after_start(cls, ends_at: datetime, info):
        starts_at = info.data.get("starts_at")
        if starts_at and ends_at <= starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at")
        return ends_at


class TimeSlotUpdate(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    capacity: int | None = None
    price: float | None = None
    is_active: bool | None = None


class TimeSlotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    court_id: UUID
    starts_at: datetime
    ends_at: datetime
    capacity: int
    price: float | None = None
    is_active: bool


class TimeSlotBulkCreate(BaseModel):
    court_ids: list[UUID]
    window_starts_at: datetime
    window_ends_at: datetime
    slot_minutes: int
    capacity: int = 1
    price: float | None = None
    is_active: bool = True

    @field_validator("court_ids")
    @classmethod
    def require_courts(cls, court_ids: list[UUID]):
        if not court_ids:
            raise ValueError("court_ids debe contener al menos una cancha")
        return court_ids

    @field_validator("window_ends_at")
    @classmethod
    def bulk_end_after_start(cls, window_ends_at: datetime, info):
        window_starts_at = info.data.get("window_starts_at")
        if window_starts_at and window_ends_at <= window_starts_at:
            raise ValueError("window_ends_at debe ser posterior a window_starts_at")
        return window_ends_at

    @field_validator("slot_minutes")
    @classmethod
    def validate_slot_minutes(cls, slot_minutes: int):
        if slot_minutes <= 0:
            raise ValueError("slot_minutes debe ser mayor a 0")
        return slot_minutes


class TimeSlotBulkCreateResult(BaseModel):
    created_count: int
    skipped_count: int
    created_slots: list[TimeSlotPublic]
    skipped_reasons: list[str]
