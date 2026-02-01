from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

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
