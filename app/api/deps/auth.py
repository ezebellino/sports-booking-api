from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.auth import oauth2_scheme
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acceso exclusivo para administradores")
    return current_user
