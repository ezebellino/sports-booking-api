from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator  # type: ignore

UserRole = Literal["admin", "staff", "user"]


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    whatsapp_number: str | None = None
    whatsapp_opt_in: bool = False

    @field_validator("whatsapp_number")
    @classmethod
    def normalize_whatsapp_number(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UserUpdate(BaseModel):
    full_name: str | None = None
    whatsapp_number: str | None = None
    whatsapp_opt_in: bool | None = None

    @field_validator("whatsapp_number")
    @classmethod
    def normalize_whatsapp_number(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    organization_id: UUID | None = None
    organization_name: str | None = None
    organization_slug: str | None = None
    whatsapp_number: str | None = None
    whatsapp_opt_in: bool
