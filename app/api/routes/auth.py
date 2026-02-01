from fastapi import APIRouter, Depends, HTTPException, status #type: ignore
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm #type: ignore
from sqlalchemy.orm import Session #type: ignore

from app.db.session import get_db #type: ignore
from app.models.user import User #type: ignore
from app.schemas.user import UserCreate, UserPublic
from app.schemas.auth import RefreshRequest, TokenPair #type: ignore
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token #type: ignore

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email ya registrado")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserPublic(id=str(user.id), email=user.email, full_name=user.full_name)

@router.post("/login", response_model=TokenPair)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas (user no existe)")

    ok = verify_password(form.password, user.hashed_password)
    if not ok:
        raise HTTPException(status_code=401, detail="Credenciales inválidas (password no matchea)")

    access = create_access_token(subject=str(user.id), extra={"email": user.email})
    refresh = create_refresh_token(subject=str(user.id))
    return TokenPair(access_token=access, refresh_token=refresh)

@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        refresh_payload = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    if refresh_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token inválido (no es refresh)")

    user_id = refresh_payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    access = create_access_token(subject=str(user.id), extra={"email": user.email})
    new_refresh = create_refresh_token(subject=str(user.id))

    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=UserPublic)
def me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserPublic(id=str(user.id), email=user.email, full_name=user.full_name)

@router.patch("/change-password", status_code=204)
def change_password(new_password: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    db.commit()
    return
