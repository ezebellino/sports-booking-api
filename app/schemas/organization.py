from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class OrganizationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_active: bool


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None


class OrganizationOnboardingCreate(BaseModel):
    organization_name: str
    organization_slug: str | None = None
    admin_full_name: str
    admin_email: EmailStr
    admin_password: str
    whatsapp_number: str | None = None
    whatsapp_opt_in: bool = False

    @field_validator("organization_name", "admin_full_name")
    @classmethod
    def trim_required_text(cls, value: str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Este campo es obligatorio")
        return normalized

    @field_validator("organization_slug")
    @classmethod
    def normalize_optional_slug(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("whatsapp_number")
    @classmethod
    def normalize_whatsapp_number(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class OrganizationOnboardingPublic(BaseModel):
    organization: OrganizationPublic
    user_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
