from fastapi import APIRouter, Depends, HTTPException
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
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserPublic, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def serialize_user(user: User) -> UserPublic:
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        whatsapp_number=user.whatsapp_number,
        whatsapp_opt_in=user.whatsapp_opt_in,
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
    return user


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email ya registrado")

    whatsapp_number = normalize_whatsapp_number(payload.whatsapp_number)
    whatsapp_opt_in = bool(payload.whatsapp_opt_in and whatsapp_number)

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role="user",
        whatsapp_number=whatsapp_number,
        whatsapp_opt_in=whatsapp_opt_in,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access = create_access_token(subject=str(user.id), extra={"email": user.email, "role": user.role})
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

    access = create_access_token(subject=str(user.id), extra={"email": user.email, "role": user.role})
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
