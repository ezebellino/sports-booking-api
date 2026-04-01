from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.auth import oauth2_scheme
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


AUTH_ERROR_DETAIL = "Token inválido o expirado"
USER_NOT_FOUND_DETAIL = "Usuario no encontrado"
ADMIN_ONLY_DETAIL = "Acceso exclusivo para administradores"


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail=AUTH_ERROR_DETAIL)

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND_DETAIL)
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail=ADMIN_ONLY_DETAIL)
    return current_user
