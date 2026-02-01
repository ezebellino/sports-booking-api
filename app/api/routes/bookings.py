from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.api.routes.auth import oauth2_scheme
from app.core.security import decode_token
from app.models.booking import Booking
from app.models.timeslot import TimeSlot
from app.schemas.booking import BookingCreate, BookingPublic
from datetime import datetime

router = APIRouter(prefix="/bookings", tags=["bookings"]) 

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    try:
        return decode_token(token)["sub"]
    except Exception:
        raise HTTPException(401, "Invalid or expired token")

@router.post("", response_model=BookingPublic, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    # Bloque sencillo: chequeo de capacidad antes de insertar
    ts: TimeSlot | None = db.get(TimeSlot, payload.timeslot_id)
    if not ts or not ts.is_active:
        raise HTTPException(404, "Timeslot not found or inactive")

    # Conteo de reservas confirmadas para ese timeslot
    confirmed = db.execute(
        select(func.count(Booking.id)).where(Booking.timeslot_id == ts.id, Booking.status == "confirmed")
    ).scalar_one()

    if confirmed >= ts.capacity:
        raise HTTPException(409, "Timeslot is full")

    b = Booking(
        user_id=user_id,
        timeslot_id=ts.id,
        status="confirmed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(b)
    try:
        db.commit()
    except IntegrityError:
        # Unique (user_id, timeslot_id) evita doble reserva del mismo usuario
        db.rollback()
        raise HTTPException(409, "You already booked this timeslot")
    db.refresh(b)
    return b

@router.get("", response_model=list[BookingPublic])
def list_bookings(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    bookings = db.execute(
        select(Booking).where(Booking.user_id == user_id)
    ).scalars().all()
    return bookings
