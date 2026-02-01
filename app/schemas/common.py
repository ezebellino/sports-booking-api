from pydantic import BaseModel, Field
from uuid import UUID

class ID(BaseModel):
    id: UUID = Field(..., description="UUID")