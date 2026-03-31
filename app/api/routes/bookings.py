from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
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
BOOKING_NOT_FOUND_DETAIL = "Reserva no encontrada"
BOOKING_ALREADY_CANCELLED_DETAIL = "La reserva ya estaba cancelada"
BOOKING_EXPIRED_DETAIL = "El turno ya no admite reservas"
BOOKING_INACTIVE_COURT_DETAIL = "La cancha está inactiva"


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    try:
        return decode_token(token)["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail=AUTH_ERROR_DETAIL)


def count_confirmed_bookings(db: Session, timeslot_id: str) -> int:
    return db.execute(
        select(func.count(Booking.id)).where(
            Booking.timeslot_id == timeslot_id,
            Booking.status == "confirmed",
        )
    ).scalar_one()


@router.post("", response_model=BookingPublic, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    timeslot = db.execute(
        select(TimeSlot)
        .options(joinedload(TimeSlot.court))
        .where(TimeSlot.id == payload.timeslot_id)
    ).scalar_one_or_none()

    if not timeslot or not timeslot.is_active:
        raise HTTPException(status_code=404, detail=BOOKING_NOT_AVAILABLE_DETAIL)

    now = datetime.now(timezone.utc)
    if timeslot.starts_at <= now:
        raise HTTPException(status_code=409, detail=BOOKING_EXPIRED_DETAIL)

    if not timeslot.court.is_active:
        raise HTTPException(status_code=409, detail=BOOKING_INACTIVE_COURT_DETAIL)

    existing_booking = db.execute(
        select(Booking).where(
            Booking.user_id == user_id,
            Booking.timeslot_id == timeslot.id,
        )
    ).scalar_one_or_none()

    if existing_booking and existing_booking.status == "confirmed":
        raise HTTPException(status_code=409, detail=BOOKING_DUPLICATE_DETAIL)

    confirmed = count_confirmed_bookings(db, timeslot.id)
    if confirmed >= timeslot.capacity:
        raise HTTPException(status_code=409, detail=BOOKING_FULL_DETAIL)

    if existing_booking and existing_booking.status == "cancelled":
        existing_booking.status = "confirmed"
        existing_booking.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing_booking)
        return existing_booking

    booking = Booking(
        user_id=user_id,
        timeslot_id=timeslot.id,
        status="confirmed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(booking)
    db.commit()
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
        .order_by(Booking.updated_at.desc(), Booking.created_at.desc())
    ).scalars().all()
    return bookings


@router.patch("/{booking_id}/cancel", response_model=BookingPublic)
def cancel_booking(booking_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    booking = db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.user_id == user_id,
        )
    ).scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail=BOOKING_NOT_FOUND_DETAIL)

    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail=BOOKING_ALREADY_CANCELLED_DETAIL)

    booking.status = "cancelled"
    booking.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(booking)
    return booking
