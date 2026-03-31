from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr # type: ignore 
from uuid import UUID

UserRole = Literal["admin", "user"]

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: UserRole

    
