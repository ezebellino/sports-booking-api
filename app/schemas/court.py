from pydantic import BaseModel 
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
    id: UUID
    venue_id: UUID
    sport_id: UUID
    name: str
    indoor: bool | None = None
    is_active: bool