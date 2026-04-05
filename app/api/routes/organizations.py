import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import (
    get_request_organization,
    require_manage_organization,
    require_manage_staff,
    require_manage_whatsapp,
)
from app.api.routes.auth import ensure_user_organization
from app.core.email import build_staff_invitation_link, send_staff_invitation_email
from app.core.logo_storage import delete_managed_logo, save_uploaded_logo
from app.core.organization_settings import get_or_create_organization_settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.core.whatsapp import normalize_whatsapp_number
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_sport import OrganizationSport
from app.models.sport import Sport
from app.models.staff_invitation import StaffInvitation
from app.models.user import User
from app.schemas.organization import (
    OrganizationOnboardingCreate,
    OrganizationOnboardingPublic,
    OrganizationPublic,
    OrganizationRequestContextPublic,
    OrganizationSettingsPublic,
    OrganizationSettingsUpdate,
    OrganizationSportsUpdate,
    OrganizationUpdate,
    StaffInvitationAccept,
    StaffInvitationAcceptancePublic,
    StaffInvitationCreate,
    StaffInvitationCreatePublic,
    StaffInvitationPublic,
)
from app.schemas.sport import OrganizationSportPublic, SportPublic

router = APIRouter(prefix="/organizations", tags=["organizations"])

ORGANIZATION_NOT_FOUND_DETAIL = "Organización no encontrada"
ORGANIZATION_NAME_EXISTS_DETAIL = "Ya existe un complejo con ese nombre"
ORGANIZATION_SLUG_EXISTS_DETAIL = "Ya existe un complejo con ese identificador"
EMAIL_EXISTS_DETAIL = "Email ya registrado"
INVITATION_NOT_FOUND_DETAIL = "Invitación no encontrada o vencida"
INVITATION_ALREADY_USED_DETAIL = "La invitación ya fue utilizada"
INVITATION_CANNOT_BE_CANCELLED_DETAIL = "Solo se pueden cancelar invitaciones pendientes"


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


def build_auth_payload(user: User) -> dict[str, str]:
    return {
        "access_token": create_access_token(
            subject=str(user.id),
            extra={
                "email": user.email,
                "role": user.role,
                "organization_id": str(user.organization_id),
            },
        ),
        "refresh_token": create_refresh_token(subject=str(user.id)),
        "token_type": "bearer",
    }


def serialize_settings(settings) -> OrganizationSettingsPublic:
    return OrganizationSettingsPublic(
        organization_id=settings.organization_id,
        branding_name=settings.branding_name,
        logo_url=settings.logo_url,
        primary_color=settings.primary_color,
        booking_min_lead_minutes=settings.booking_min_lead_minutes,
        cancellation_min_lead_minutes=settings.cancellation_min_lead_minutes,
        whatsapp_provider=settings.whatsapp_provider,
        whatsapp_phone_number_id=settings.whatsapp_phone_number_id,
        whatsapp_template_language=settings.whatsapp_template_language,
        whatsapp_template_booking_confirmed=settings.whatsapp_template_booking_confirmed,
        whatsapp_template_booking_cancelled=settings.whatsapp_template_booking_cancelled,
        whatsapp_recipient_override=settings.whatsapp_recipient_override,
        has_whatsapp_access_token=bool(settings.whatsapp_access_token),
    )


def ensure_organization_sport_rows(db: Session, organization: Organization) -> list[OrganizationSport]:
    sports = db.query(Sport).order_by(Sport.name.asc()).all()
    existing = {
        row.sport_id: row
        for row in db.query(OrganizationSport).filter(OrganizationSport.organization_id == organization.id).all()
    }

    created = False
    for sport in sports:
        if sport.id not in existing:
            row = OrganizationSport(organization_id=organization.id, sport_id=sport.id, is_enabled=True)
            db.add(row)
            existing[sport.id] = row
            created = True

    if created:
        db.commit()
        for row in existing.values():
            db.refresh(row)

    return [existing[sport.id] for sport in sports]


@router.get("/request-context", response_model=OrganizationRequestContextPublic)
def get_request_context(
    organization: Organization = Depends(get_request_organization),
    db: Session = Depends(get_db),
):
    settings = get_or_create_organization_settings(db, organization)
    return OrganizationRequestContextPublic(
        organization=organization,
        branding_name=settings.branding_name,
        logo_url=settings.logo_url,
        primary_color=settings.primary_color,
    )


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

    settings = get_or_create_organization_settings(db, organization)
    settings.branding_name = payload.organization_name
    db.add(settings)
    db.flush()

    for sport in db.query(Sport).all():
        db.add(OrganizationSport(organization_id=organization.id, sport_id=sport.id, is_enabled=True))

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

    tokens = build_auth_payload(admin_user)
    return OrganizationOnboardingPublic(
        organization=organization,
        user_id=admin_user.id,
        **tokens,
    )


@router.get("/current", response_model=OrganizationPublic)
def get_current_organization(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_organization),
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
    current_admin: User = Depends(require_manage_organization),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return organization

    if "name" in data and data["name"]:
        clash = db.query(Organization).filter(Organization.name.ilike(data["name"]), Organization.id != organization.id).first()
        if clash:
            raise HTTPException(status_code=409, detail=ORGANIZATION_NAME_EXISTS_DETAIL)
        organization.name = data["name"].strip()

    if "slug" in data and data["slug"]:
        normalized_slug = slugify_organization_name(data["slug"])
        clash = db.query(Organization).filter(Organization.slug == normalized_slug, Organization.id != organization.id).first()
        if clash:
            raise HTTPException(status_code=409, detail=ORGANIZATION_SLUG_EXISTS_DETAIL)
        organization.slug = normalized_slug

    if "is_active" in data and data["is_active"] is not None:
        organization.is_active = data["is_active"]

    db.commit()
    db.refresh(organization)
    return organization


@router.get("/current/settings", response_model=OrganizationSettingsPublic)
def get_current_organization_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_organization),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)
    settings = get_or_create_organization_settings(db, organization)
    return serialize_settings(settings)


@router.get("/current/sports", response_model=list[OrganizationSportPublic])
def list_current_organization_sports(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_organization),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)

    rows = ensure_organization_sport_rows(db, organization)
    return [OrganizationSportPublic(sport=SportPublic.model_validate(row.sport), is_enabled=row.is_enabled) for row in rows]


@router.patch("/current/sports", response_model=list[OrganizationSportPublic])
def update_current_organization_sports(
    payload: OrganizationSportsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_organization),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)

    rows = ensure_organization_sport_rows(db, organization)
    enabled_ids = {str(item) for item in payload.enabled_sport_ids}

    for row in rows:
        row.is_enabled = str(row.sport_id) in enabled_ids
        db.add(row)

    db.commit()
    for row in rows:
        db.refresh(row)

    return [OrganizationSportPublic(sport=SportPublic.model_validate(row.sport), is_enabled=row.is_enabled) for row in rows]


@router.patch("/current/settings", response_model=OrganizationSettingsPublic)
def update_current_organization_settings(
    payload: OrganizationSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_whatsapp),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)
    settings = get_or_create_organization_settings(db, organization)

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "whatsapp_recipient_override":
            value = normalize_whatsapp_number(value)
        setattr(settings, field, value)

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return serialize_settings(settings)


@router.post("/current/logo", response_model=OrganizationSettingsPublic)
async def upload_current_organization_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_staff),
):
    current_admin = ensure_user_organization(db, current_admin)
    organization = db.get(Organization, current_admin.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)

    settings = get_or_create_organization_settings(db, organization)
    previous_logo_url = settings.logo_url
    settings.logo_url = await save_uploaded_logo(file, organization.id)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    delete_managed_logo(previous_logo_url)
    return serialize_settings(settings)


@router.get("/current/staff-invitations", response_model=list[StaffInvitationPublic])
def list_staff_invitations(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_staff),
):
    current_admin = ensure_user_organization(db, current_admin)
    now = datetime.now(timezone.utc)
    invitations = (
        db.query(StaffInvitation)
        .filter(
            StaffInvitation.organization_id == current_admin.organization_id,
            StaffInvitation.status == "pending",
            StaffInvitation.expires_at > now,
        )
        .order_by(StaffInvitation.created_at.desc())
        .all()
    )
    return invitations


@router.post("/current/staff-invitations", response_model=StaffInvitationCreatePublic, status_code=201)
def create_staff_invitation(
    payload: StaffInvitationCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_staff),
):
    current_admin = ensure_user_organization(db, current_admin)
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail=EMAIL_EXISTS_DETAIL)

    invitation = StaffInvitation(
        organization_id=current_admin.organization_id,
        invited_by_user_id=current_admin.id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        invite_token=secrets.token_urlsafe(24),
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    organization = db.get(Organization, current_admin.organization_id)
    delivery_status, delivery_detail = send_staff_invitation_email(
        recipient_email=invitation.email,
        recipient_name=invitation.full_name,
        organization_name=organization.name if organization else "tu complejo",
        inviter_name=current_admin.full_name or current_admin.email,
        role=invitation.role,
        invite_token=invitation.invite_token,
    )
    return StaffInvitationCreatePublic(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        full_name=invitation.full_name,
        role=invitation.role,
        status=invitation.status,
        invite_token=invitation.invite_token,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        invite_url=build_staff_invitation_link(invitation.invite_token),
        email_delivery_status=delivery_status,
        email_delivery_detail=delivery_detail,
    )


@router.delete("/current/staff-invitations/{invitation_id}", response_model=StaffInvitationPublic)
def cancel_staff_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_staff),
):
    current_admin = ensure_user_organization(db, current_admin)
    invitation = (
        db.query(StaffInvitation)
        .filter(
            StaffInvitation.id == invitation_id,
            StaffInvitation.organization_id == current_admin.organization_id,
        )
        .first()
    )
    if not invitation:
        raise HTTPException(status_code=404, detail=INVITATION_NOT_FOUND_DETAIL)
    if invitation.status != "pending":
        raise HTTPException(status_code=409, detail=INVITATION_CANNOT_BE_CANCELLED_DETAIL)

    invitation.status = "cancelled"
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.post("/staff-invitations/accept", response_model=StaffInvitationAcceptancePublic)
def accept_staff_invitation(payload: StaffInvitationAccept, db: Session = Depends(get_db)):
    invitation = (
        db.query(StaffInvitation)
        .options(joinedload(StaffInvitation.organization))
        .filter(StaffInvitation.invite_token == payload.token)
        .first()
    )
    if not invitation or invitation.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=404, detail=INVITATION_NOT_FOUND_DETAIL)
    if invitation.status != "pending":
        raise HTTPException(status_code=409, detail=INVITATION_ALREADY_USED_DETAIL)
    if db.query(User).filter(User.email == invitation.email).first():
        raise HTTPException(status_code=409, detail=EMAIL_EXISTS_DETAIL)

    whatsapp_number = normalize_whatsapp_number(payload.whatsapp_number)
    whatsapp_opt_in = bool(payload.whatsapp_opt_in and whatsapp_number)

    user = User(
        email=invitation.email,
        full_name=(payload.full_name or invitation.full_name or "").strip() or None,
        hashed_password=get_password_hash(payload.password),
        role=invitation.role,
        organization_id=invitation.organization_id,
        whatsapp_number=whatsapp_number,
        whatsapp_opt_in=whatsapp_opt_in,
    )
    db.add(user)

    invitation.status = "accepted"
    invitation.accepted_at = datetime.now(timezone.utc)
    db.add(invitation)
    (
        db.query(StaffInvitation)
        .filter(
            StaffInvitation.organization_id == invitation.organization_id,
            StaffInvitation.email == invitation.email,
            StaffInvitation.status == "pending",
            StaffInvitation.id != invitation.id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    db.refresh(user)
    db.refresh(invitation)

    tokens = build_auth_payload(user)
    return StaffInvitationAcceptancePublic(
        organization=invitation.organization,
        user_id=user.id,
        **tokens,
    )
