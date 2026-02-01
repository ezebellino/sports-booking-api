from pydantic import BaseModel
from uuid import UUID

class SportCreate(BaseModel):
    name: str
    description: str | None = None
    
class SportUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    
class SportPublic(BaseModel):
    id: UUID
    name: str
    description: str | None = None