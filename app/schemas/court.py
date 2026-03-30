from pydantic import BaseModel, ConfigDict 
from uuid import UUID

class CourtCreate(BaseModel):
    venue_id: UUID
    sport_id: UUID
    name: str
    indoor: bool | None = None
    is_active: bool = True # si la cancha está disponible para reservas
    
class CourtUpdate(BaseModel):
    name: str | None = None
    indoor: bool | None = None
    is_active: bool | None = None 
    
class CourtPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    venue_id: UUID
    sport_id: UUID
    name: str
    indoor: bool | None = None
    is_active: bool
