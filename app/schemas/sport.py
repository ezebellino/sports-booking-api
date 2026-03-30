from pydantic import BaseModel, ConfigDict
from uuid import UUID

class SportCreate(BaseModel):
    name: str
    description: str | None = None
    
class SportUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    
class SportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
