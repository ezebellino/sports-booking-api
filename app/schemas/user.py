from pydantic import BaseModel, EmailStr # type: ignore 


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None

    
