from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.routes.auth import (
    ensure_user_organization,
    get_default_organization,
    get_request_organization_from_request,
    get_requested_organization_slug_from_request,
    oauth2_optional,
    oauth2_scheme,
    require_request_organization_from_request,
)
from app.core.security import decode_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User


AUTH_ERROR_DETAIL = "Token inválido o expirado"
USER_NOT_FOUND_DETAIL = "Usuario no encontrado"
ADMIN_ONLY_DETAIL = "Acceso exclusivo para administradores"
STAFF_ONLY_DETAIL = "Acceso exclusivo para staff operativo o administradores"


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail=AUTH_ERROR_DETAIL)

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_DETAIL)
    return ensure_user_organization(db, user)


def get_optional_current_user(token: str | None = Depends(oauth2_optional), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except Exception:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if not user:
        return None
    return ensure_user_organization(db, user)


def get_current_organization(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Organization:
    if current_user.organization_id:
        organization = db.get(Organization, current_user.organization_id)
        if organization:
            return organization
    return get_default_organization(db)


def get_request_organization(
    current_user: User | None = Depends(get_optional_current_user),
    request: Request = None,
    db: Session = Depends(get_db),
) -> Organization:
    if current_user and current_user.organization_id:
        organization = db.get(Organization, current_user.organization_id)
        if organization:
            return organization

    if request is not None and get_requested_organization_slug_from_request(request):
        return require_request_organization_from_request(db, request)

    if request is not None:
        return get_request_organization_from_request(db, request)

    return get_default_organization(db)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail=ADMIN_ONLY_DETAIL)
    return current_user


def require_staff_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail=STAFF_ONLY_DETAIL)
    return current_user
