import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin
from app.api.routes.auth import ensure_user_organization, serialize_user
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.core.whatsapp import normalize_whatsapp_number
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    OrganizationOnboardingCreate,
    OrganizationOnboardingPublic,
    OrganizationPublic,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])

ORGANIZATION_NOT_FOUND_DETAIL = "Organización no encontrada"
ORGANIZATION_NAME_EXISTS_DETAIL = "Ya existe un complejo con ese nombre"
ORGANIZATION_SLUG_EXISTS_DETAIL = "Ya existe un complejo con ese identificador"
EMAIL_EXISTS_DETAIL = "Email ya registrado"


def slugify_organization_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return normalized or "complejo"


def unique_organization_slug(db: Session, requested_slug: str) -> str:
    base_slug = slugify_organization_name(requested_slug)
    slug = base_slug
    suffix = 2

    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    return slug


@router.post("/onboard", response_model=OrganizationOnboardingPublic, status_code=201)
def onboard_organization(payload: OrganizationOnboardingCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(status_code=409, detail=EMAIL_EXISTS_DETAIL)

    if db.query(Organization).filter(Organization.name.ilike(payload.organization_name)).first():
        raise HTTPException(status_code=409, detail=ORGANIZATION_NAME_EXISTS_DETAIL)

    requested_slug = payload.organization_slug or payload.organization_name
    if payload.organization_slug and db.query(Organization).filter(Organization.slug == payload.organization_slug).first():
        raise HTTPException(status_code=409, detail=ORGANIZATION_SLUG_EXISTS_DETAIL)

    organization = Organization(
        name=payload.organization_name,
        slug=unique_organization_slug(db, requested_slug),
        is_active=True,
    )
    db.add(organization)
    db.flush()

    whatsapp_number = normalize_whatsapp_number(payload.whatsapp_number)
    whatsapp_opt_in = bool(payload.whatsapp_opt_in and whatsapp_number)

    admin_user = User(
        email=payload.admin_email,
        full_name=payload.admin_full_name,
        hashed_password=get_password_hash(payload.admin_password),
        role="admin",
        organization_id=organization.id,
        whatsapp_number=whatsapp_number,
        whatsapp_opt_in=whatsapp_opt_in,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(organization)
    db.refresh(admin_user)

    access_token = create_access_token(
        subject=str(admin_user.id),
        extra={
            "email": admin_user.email,
            "role": admin_user.role,
            "organization_id": str(admin_user.organization_id),
        },
    )
    refresh_token = create_refresh_token(subject=str(admin_user.id))

    return OrganizationOnboardingPublic(
        organization=organization,
        user_id=admin_user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get("/current", response_model=OrganizationPublic)
def get_current_organization(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)
    return organization


@router.patch("/current", response_model=OrganizationPublic)
def update_current_organization(
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return organization

    if "name" in data and data["name"]:
        clash = (
            db.query(Organization)
            .filter(Organization.name.ilike(data["name"]), Organization.id != organization.id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail=ORGANIZATION_NAME_EXISTS_DETAIL)
        organization.name = data["name"].strip()

    if "slug" in data and data["slug"]:
        clash = (
            db.query(Organization)
            .filter(Organization.slug == data["slug"], Organization.id != organization.id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail=ORGANIZATION_SLUG_EXISTS_DETAIL)
        organization.slug = slugify_organization_name(data["slug"])

    if "is_active" in data and data["is_active"] is not None:
        organization.is_active = data["is_active"]

    db.commit()
    db.refresh(organization)
    return organization
