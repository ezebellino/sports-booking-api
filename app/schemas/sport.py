from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SportCreate(BaseModel):
    name: str
    description: str | None = None
    booking_min_lead_minutes: int | None = Field(default=None, ge=0)
    cancellation_min_lead_minutes: int | None = Field(default=None, ge=0)


class SportUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    booking_min_lead_minutes: int | None = Field(default=None, ge=0)
    cancellation_min_lead_minutes: int | None = Field(default=None, ge=0)


class SportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    booking_min_lead_minutes: int | None = None
    cancellation_min_lead_minutes: int | None = None
