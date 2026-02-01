from pydantic import BaseModel, field_validator
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
    id: UUID
    court_id: UUID
    starts_at: datetime
    ends_at: datetime
    capacity: int
    price: float | None = None
    is_active: bool
