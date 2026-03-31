from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import AUTH_ERROR_DETAIL
from app.api.routes.auth import oauth2_scheme
from app.core.security import decode_token
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.timeslot import TimeSlot
from app.schemas.booking import BookingCreate, BookingDetailPublic, BookingPublic

router = APIRouter(prefix="/bookings", tags=["bookings"])

BOOKING_NOT_AVAILABLE_DETAIL = "Turno no disponible"
BOOKING_FULL_DETAIL = "El turno ya está completo"
BOOKING_DUPLICATE_DETAIL = "Ya reservaste este turno"


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    try:
        return decode_token(token)["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail=AUTH_ERROR_DETAIL)


@router.post("", response_model=BookingPublic, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    timeslot: TimeSlot | None = db.get(TimeSlot, payload.timeslot_id)
    if not timeslot or not timeslot.is_active:
        raise HTTPException(status_code=404, detail=BOOKING_NOT_AVAILABLE_DETAIL)

    confirmed = db.execute(
        select(func.count(Booking.id)).where(Booking.timeslot_id == timeslot.id, Booking.status == "confirmed")
    ).scalar_one()

    if confirmed >= timeslot.capacity:
        raise HTTPException(status_code=409, detail=BOOKING_FULL_DETAIL)

    booking = Booking(
        user_id=user_id,
        timeslot_id=timeslot.id,
        status="confirmed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=BOOKING_DUPLICATE_DETAIL)

    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingDetailPublic])
def list_bookings(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    bookings = db.execute(
        select(Booking)
        .options(
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.venue),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.sport),
        )
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    ).scalars().all()
    return bookings