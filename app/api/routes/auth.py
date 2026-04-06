from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import set_committed_value

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.organization_memberships import ensure_membership
from app.core.whatsapp import normalize_whatsapp_number
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserPermissionsPublic, UserPublic, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DEFAULT_ORGANIZATION_SLUG = "complejo-demo"
TENANT_MISMATCH_DETAIL = "Esta cuenta pertenece a otro complejo"
ORGANIZATION_NOT_FOUND_DETAIL = "Complejo no encontrado"
ORGANIZATION_INACTIVE_DETAIL = "Este complejo está desactivado"
NO_MEMBERSHIP_DETAIL = "Esta cuenta no tiene acceso a ningún complejo"


def get_default_organization(db: Session) -> Organization:
    organization = db.query(Organization).filter(Organization.slug == DEFAULT_ORGANIZATION_SLUG).first()
    if not organization:
        organization = Organization(name="Complejo Demo", slug=DEFAULT_ORGANIZATION_SLUG, is_active=True)
        db.add(organization)
        db.commit()
        db.refresh(organization)
    return organization


def get_organization_by_slug(db: Session, slug: str | None) -> Organization | None:
    normalized = (slug or "").strip().lower()
    if not normalized:
        return None
    return db.query(Organization).filter(Organization.slug == normalized).first()


def get_requested_organization_slug_from_request(request: Request) -> str | None:
    requested_slug = request.headers.get("X-Organization-Slug")
    normalized = (requested_slug or "").strip().lower()
    return normalized or None


def require_request_organization_from_request(db: Session, request: Request) -> Organization:
    requested_slug = get_requested_organization_slug_from_request(request)
    if not requested_slug:
        return get_default_organization(db)

    requested_organization = get_organization_by_slug(db, requested_slug)
    if not requested_organization:
        raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)

    return requested_organization


def get_request_organization_from_request(db: Session, request: Request) -> Organization:
    requested_slug = get_requested_organization_slug_from_request(request)
    requested_organization = get_organization_by_slug(db, requested_slug)
    if requested_organization:
        return requested_organization
    return get_default_organization(db)


def ensure_public_organization_is_active(organization: Organization) -> Organization:
    if not organization.is_active:
        raise HTTPException(status_code=403, detail=ORGANIZATION_INACTIVE_DETAIL)
    return organization


def ensure_user_organization(db: Session, user: User) -> User:
    if user.organization_id:
        return user

    default_organization = get_default_organization(db)
    user.organization_id = default_organization.id
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_user_membership(db: Session, user: User) -> User:
    user = ensure_user_organization(db, user)
    memberships = db.query(OrganizationMembership).filter(OrganizationMembership.user_id == user.id).all()
    membership = next((item for item in memberships if item.organization_id == user.organization_id), None)
    if membership:
        if len(memberships) == 1 and membership.role != user.role:
            membership.role = user.role
            membership.is_default = True
            db.add(membership)
            db.commit()
        return user

    organization = user.organization or db.get(Organization, user.organization_id)
    if organization is None:
        raise HTTPException(status_code=403, detail=NO_MEMBERSHIP_DETAIL)
    ensure_membership(db, user=user, organization=organization, role=user.role, make_default=True)
    db.commit()
    db.refresh(user)
    return user


def list_user_memberships(db: Session, user: User) -> list[OrganizationMembership]:
    ensure_user_membership(db, user)
    return (
        db.query(OrganizationMembership)
        .options(joinedload(OrganizationMembership.organization))
        .filter(OrganizationMembership.user_id == user.id)
        .all()
    )


def apply_active_membership(user: User, membership: OrganizationMembership) -> User:
    organization = membership.organization
    if organization is not None:
        set_committed_value(user, "organization", organization)
    set_committed_value(user, "organization_id", membership.organization_id)
    set_committed_value(user, "role", membership.role)
    setattr(user, "_active_membership", membership)
    return user


def resolve_active_membership(
    db: Session,
    user: User,
    *,
    organization: Organization | None = None,
    organization_id: str | None = None,
    strict: bool = False,
) -> OrganizationMembership:
    memberships = list_user_memberships(db, user)
    if not memberships:
        raise HTTPException(status_code=403, detail=NO_MEMBERSHIP_DETAIL)

    target_organization_id = str(organization.id) if organization else organization_id
    membership: OrganizationMembership | None = None

    if target_organization_id:
        membership = next(
            (item for item in memberships if str(item.organization_id) == str(target_organization_id)),
            None,
        )
        if not membership and strict:
            raise HTTPException(status_code=403, detail=TENANT_MISMATCH_DETAIL)

    if membership is None:
        membership = next((item for item in memberships if item.is_default), None) or memberships[0]

    apply_active_membership(user, membership)
    return membership


def ensure_user_can_access_organization(
    db: Session,
    user: User,
    *,
    organization: Organization | None = None,
    organization_id: str | None = None,
    strict: bool = False,
) -> User:
    membership = resolve_active_membership(
        db,
        user,
        organization=organization,
        organization_id=organization_id,
        strict=strict,
    )
    active_organization = membership.organization or db.get(Organization, membership.organization_id)
    if active_organization and not active_organization.is_active and membership.role != "admin":
        raise HTTPException(status_code=403, detail=ORGANIZATION_INACTIVE_DETAIL)
    return user


def build_user_permissions(user: User) -> UserPermissionsPublic:
    active_membership = getattr(user, "_active_membership", None)
    active_role = active_membership.role if active_membership is not None else user.role

    if active_role == "admin":
        return UserPermissionsPublic(
            manage_organization=True,
            manage_staff=True,
            view_metrics=True,
            manage_inventory=True,
            manage_timeslots=True,
            manage_whatsapp=True,
        )

    if active_role == "staff":
        return UserPermissionsPublic(
            manage_organization=False,
            manage_staff=False,
            view_metrics=True,
            manage_inventory=True,
            manage_timeslots=True,
            manage_whatsapp=False,
        )

    return UserPermissionsPublic(
        manage_organization=False,
        manage_staff=False,
        view_metrics=False,
        manage_inventory=False,
        manage_timeslots=False,
        manage_whatsapp=False,
    )


def serialize_user(user: User, db: Session | None = None) -> UserPublic:
    active_membership = getattr(user, "_active_membership", None)
    if db is not None and active_membership is None:
        user = ensure_user_can_access_organization(db, user)
        active_membership = getattr(user, "_active_membership", None)

    active_organization = (
        active_membership.organization
        if active_membership is not None
        else user.organization
    )
    active_organization_id = (
        active_membership.organization_id
        if active_membership is not None
        else user.organization_id
    )
    active_role = active_membership.role if active_membership is not None else user.role

    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=active_role,
        organization_id=active_organization_id,
        organization_name=active_organization.name if active_organization else None,
        organization_slug=active_organization.slug if active_organization else None,
        whatsapp_number=user.whatsapp_number,
        whatsapp_opt_in=user.whatsapp_opt_in,
        permissions=build_user_permissions(user),
    )


def build_auth_payload(db: Session, user: User, organization: Organization | None = None) -> dict[str, str]:
    active_membership = getattr(user, "_active_membership", None)
    if organization is not None:
        user = ensure_user_can_access_organization(db, user, organization=organization, strict=True)
        active_membership = getattr(user, "_active_membership", None)
    elif active_membership is None:
        user = ensure_user_can_access_organization(db, user)
        active_membership = getattr(user, "_active_membership", None)

    active_organization_id = (
        str(active_membership.organization_id)
        if active_membership is not None
        else (str(user.organization_id) if user.organization_id else None)
    )
    active_role = active_membership.role if active_membership is not None else user.role

    return {
        "access_token": create_access_token(
            subject=str(user.id),
            extra={
                "email": user.email,
                "role": active_role,
                "organization_id": active_organization_id,
            },
        ),
        "refresh_token": create_refresh_token(
            subject=str(user.id),
            extra={
                "organization_id": active_organization_id,
            },
        ),
        "token_type": "bearer",
    }


def get_current_user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    token_organization_id = payload.get("organization_id")
    return ensure_user_can_access_organization(
        db,
        user,
        organization_id=token_organization_id,
        strict=bool(token_organization_id),
    )


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    whatsapp_number = normalize_whatsapp_number(payload.whatsapp_number)
    whatsapp_opt_in = bool(payload.whatsapp_opt_in and whatsapp_number)
    target_organization = ensure_public_organization_is_active(get_request_organization_from_request(db, request))

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role="user",
        organization_id=target_organization.id,
        whatsapp_number=whatsapp_number,
        whatsapp_opt_in=whatsapp_opt_in,
    )
    db.add(user)
    db.flush()
    ensure_membership(db, user=user, organization=target_organization, role="user", make_default=True)
    db.commit()
    db.refresh(user)
    return serialize_user(user, db)


@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), request: Request = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    requested_slug = get_requested_organization_slug_from_request(request) if request is not None else None
    requested_organization = None
    if requested_slug:
        requested_organization = get_organization_by_slug(db, requested_slug)
        if not requested_organization:
            raise HTTPException(status_code=404, detail=ORGANIZATION_NOT_FOUND_DETAIL)
    user = ensure_user_can_access_organization(
        db,
        user,
        organization=requested_organization,
        strict=bool(requested_slug),
    )
    tokens = build_auth_payload(db, user)
    return TokenPair(access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        refresh_payload = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    if refresh_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    user_id = refresh_payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    refresh_organization_id = refresh_payload.get("organization_id")
    user = ensure_user_can_access_organization(
        db,
        user,
        organization_id=refresh_organization_id,
        strict=bool(refresh_organization_id),
    )

    tokens = build_auth_payload(db, user)
    return TokenPair(access_token=tokens["access_token"], refresh_token=tokens["refresh_token"])


@router.get("/me", response_model=UserPublic)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)
    return serialize_user(user, db)


@router.patch("/me", response_model=UserPublic)
def update_me(payload: UserUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return serialize_user(user)

    if "full_name" in data:
        user.full_name = data["full_name"]

    if "whatsapp_number" in data:
        user.whatsapp_number = normalize_whatsapp_number(data["whatsapp_number"])
        if not user.whatsapp_number:
            user.whatsapp_opt_in = False

    if "whatsapp_opt_in" in data:
        user.whatsapp_opt_in = bool(data["whatsapp_opt_in"] and user.whatsapp_number)

    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user, db)


@router.patch("/change-password", status_code=204)
def change_password(new_password: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    db.commit()
