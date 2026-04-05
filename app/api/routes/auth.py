from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.whatsapp import normalize_whatsapp_number
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserPermissionsPublic, UserPublic, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DEFAULT_ORGANIZATION_SLUG = "complejo-demo"
TENANT_MISMATCH_DETAIL = "Esta cuenta pertenece a otro complejo"
ORGANIZATION_NOT_FOUND_DETAIL = "Complejo no encontrado"


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


def ensure_user_organization(db: Session, user: User) -> User:
    if user.organization_id:
        return user

    default_organization = get_default_organization(db)
    user.organization_id = default_organization.id
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def build_user_permissions(user: User) -> UserPermissionsPublic:
    if user.role == "admin":
        return UserPermissionsPublic(
            manage_organization=True,
            manage_staff=True,
            view_metrics=True,
            manage_inventory=True,
            manage_timeslots=True,
            manage_whatsapp=True,
        )

    if user.role == "staff":
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


def serialize_user(user: User) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        organization_id=user.organization_id,
        organization_name=user.organization.name if user.organization else None,
        organization_slug=user.organization.slug if user.organization else None,
        whatsapp_number=user.whatsapp_number,
        whatsapp_opt_in=user.whatsapp_opt_in,
        permissions=build_user_permissions(user),
    )


def get_current_user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return ensure_user_organization(db, user)


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    whatsapp_number = normalize_whatsapp_number(payload.whatsapp_number)
    whatsapp_opt_in = bool(payload.whatsapp_opt_in and whatsapp_number)
    target_organization = get_request_organization_from_request(db, request)

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
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), request: Request = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    user = ensure_user_organization(db, user)
    requested_organization = get_request_organization_from_request(db, request)
    if user.organization_id != requested_organization.id:
        raise HTTPException(status_code=403, detail=TENANT_MISMATCH_DETAIL)

    access = create_access_token(
        subject=str(user.id),
        extra={
            "email": user.email,
            "role": user.role,
            "organization_id": str(user.organization_id) if user.organization_id else None,
        },
    )
    refresh = create_refresh_token(subject=str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh)


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
    user = ensure_user_organization(db, user)

    access = create_access_token(
        subject=str(user.id),
        extra={
            "email": user.email,
            "role": user.role,
            "organization_id": str(user.organization_id) if user.organization_id else None,
        },
    )
    new_refresh = create_refresh_token(subject=str(user.id))
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserPublic)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)
    return serialize_user(user)


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
    return serialize_user(user)


@router.patch("/change-password", status_code=204)
def change_password(new_password: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user_from_token(token, db)
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    db.commit()
