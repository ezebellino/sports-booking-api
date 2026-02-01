from pydantic import BaseModel
from uuid import UUID

class VenueCreate(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "America/Argentina/Buenos_Aires"
    allowed_sport_id: UUID | None = None # sport_id permitido para este venue, si es None permite todos
    
class VenueUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    allowed_sport_id: UUID | None = None
    
class VenuePublic(BaseModel):
    id: UUID
    name: str
    address: str | None = None
    timezone: str
    allowed_sport_id: UUID | None = None