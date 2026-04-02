from datetime import datetime
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


class OrganizationSettingsPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: UUID
    branding_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    booking_min_lead_minutes: int | None = None
    cancellation_min_lead_minutes: int | None = None
    whatsapp_provider: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_template_language: str | None = None
    whatsapp_template_booking_confirmed: str | None = None
    whatsapp_template_booking_cancelled: str | None = None
    whatsapp_recipient_override: str | None = None
    has_whatsapp_access_token: bool = False


class OrganizationRequestContextPublic(BaseModel):
    organization: OrganizationPublic
    branding_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None


class OrganizationSettingsUpdate(BaseModel):
    branding_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    booking_min_lead_minutes: int | None = None
    cancellation_min_lead_minutes: int | None = None
    whatsapp_provider: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_template_language: str | None = None
    whatsapp_template_booking_confirmed: str | None = None
    whatsapp_template_booking_cancelled: str | None = None
    whatsapp_recipient_override: str | None = None

    @field_validator(
        "branding_name",
        "logo_url",
        "primary_color",
        "whatsapp_provider",
        "whatsapp_access_token",
        "whatsapp_phone_number_id",
        "whatsapp_template_language",
        "whatsapp_template_booking_confirmed",
        "whatsapp_template_booking_cancelled",
        "whatsapp_recipient_override",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("booking_min_lead_minutes", "cancellation_min_lead_minutes")
    @classmethod
    def validate_non_negative_minutes(cls, value: int | None):
        if value is None:
            return None
        if value < 0:
            raise ValueError("Los minutos no pueden ser negativos")
        return value


class StaffInvitationCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: str = "user"
    expires_in_days: int = 7

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str):
        normalized = value.strip().lower()
        if normalized not in {"admin", "staff", "user"}:
            raise ValueError("El rol debe ser admin, staff o user")
        return normalized

    @field_validator("expires_in_days")
    @classmethod
    def validate_expiry_days(cls, value: int):
        if value < 1 or value > 90:
            raise ValueError("La invitación debe vencer entre 1 y 90 días")
        return value


class StaffInvitationAccept(BaseModel):
    token: str
    full_name: str | None = None
    password: str
    whatsapp_number: str | None = None
    whatsapp_opt_in: bool = False

    @field_validator("token", "password")
    @classmethod
    def trim_required_values(cls, value: str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("Este campo es obligatorio")
        return normalized

    @field_validator("full_name", "whatsapp_number")
    @classmethod
    def normalize_optional_accept_values(cls, value: str | None):
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class StaffInvitationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    email: EmailStr
    full_name: str | None = None
    role: str
    status: str
    invite_token: str
    expires_at: datetime
    accepted_at: datetime | None = None


class StaffInvitationAcceptancePublic(BaseModel):
    organization: OrganizationPublic
    user_id: UUID
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
