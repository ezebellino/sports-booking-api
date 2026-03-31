from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import AUTH_ERROR_DETAIL
from app.api.routes.auth import oauth2_scheme
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.timeslot import TimeSlot
from app.schemas.booking import BookingCreate, BookingDetailPublic, BookingPolicyPublic, BookingPublic

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


def count_confirmed_bookings(db: Session, timeslot_id) -> int:
    return int(
        db.execute(
            select(func.count(Booking.id)).where(
                Booking.timeslot_id == timeslot_id,
                Booking.status == "confirmed",
            )
        ).scalar_one()
    )


def booking_cutoff_delta() -> timedelta:
    return timedelta(minutes=settings.BOOKING_MIN_LEAD_MINUTES)


def cancellation_cutoff_delta() -> timedelta:
    return timedelta(minutes=settings.CANCELLATION_MIN_LEAD_MINUTES)


def booking_policy_message() -> str:
    return f"Las reservas deben hacerse con al menos {settings.BOOKING_MIN_LEAD_MINUTES} minutos de anticipación."


def cancellation_policy_message() -> str:
    return f"Las cancelaciones se permiten hasta {settings.CANCELLATION_MIN_LEAD_MINUTES} minutos antes del inicio del turno."


def booking_policy_payload() -> BookingPolicyPublic:
    return BookingPolicyPublic(
        min_booking_lead_minutes=settings.BOOKING_MIN_LEAD_MINUTES,
        cancellation_min_lead_minutes=settings.CANCELLATION_MIN_LEAD_MINUTES,
        booking_message=booking_policy_message(),
        cancellation_message=cancellation_policy_message(),
    )


def validate_booking_window(timeslot: TimeSlot, now: datetime) -> None:
    if timeslot.starts_at <= now:
        raise HTTPException(status_code=409, detail=BOOKING_EXPIRED_DETAIL)
    if timeslot.starts_at < now + booking_cutoff_delta():
        raise HTTPException(status_code=409, detail=booking_policy_message())


def derive_availability_status(timeslot: TimeSlot, confirmed_bookings: int, now: datetime) -> str:
    remaining_spots = max(timeslot.capacity - confirmed_bookings, 0)

    if not timeslot.is_active or not timeslot.court.is_active:
        return "inactive"
    if timeslot.starts_at <= now:
        return "expired"
    if timeslot.starts_at < now + booking_cutoff_delta():
        return "booking_closed"
    if remaining_spots <= 0:
        return "full"
    if remaining_spots == 1:
        return "few_left"
    return "available"


def serialize_booking_detail(booking: Booking, db: Session, now: datetime | None = None) -> BookingDetailPublic:
    now = now or datetime.now(timezone.utc)
    confirmed_bookings = count_confirmed_bookings(db, booking.timeslot.id)
    remaining_spots = max(booking.timeslot.capacity - confirmed_bookings, 0)
    cancellation_deadline = booking.timeslot.starts_at - cancellation_cutoff_delta()
    can_cancel = (
        booking.status == "confirmed"
        and booking.timeslot.starts_at > now
        and now < cancellation_deadline
    )
    availability_status = derive_availability_status(booking.timeslot, confirmed_bookings, now)

    return BookingDetailPublic.model_validate(
        {
            "id": booking.id,
            "user_id": booking.user_id,
            "timeslot_id": booking.timeslot_id,
            "status": booking.status,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at,
            "can_cancel": can_cancel,
            "cancellation_deadline": cancellation_deadline,
            "cancellation_policy_message": cancellation_policy_message(),
            "timeslot": {
                "id": booking.timeslot.id,
                "court_id": booking.timeslot.court_id,
                "starts_at": booking.timeslot.starts_at,
                "ends_at": booking.timeslot.ends_at,
                "capacity": booking.timeslot.capacity,
                "price": booking.timeslot.price,
                "is_active": booking.timeslot.is_active,
                "confirmed_bookings": confirmed_bookings,
                "remaining_spots": remaining_spots,
                "availability_status": availability_status,
                "court": {
                    "id": booking.timeslot.court.id,
                    "venue_id": booking.timeslot.court.venue_id,
                    "sport_id": booking.timeslot.court.sport_id,
                    "name": booking.timeslot.court.name,
                    "indoor": booking.timeslot.court.indoor,
                    "is_active": booking.timeslot.court.is_active,
                    "venue": {
                        "id": booking.timeslot.court.venue.id,
                        "name": booking.timeslot.court.venue.name,
                        "address": booking.timeslot.court.venue.address,
                        "timezone": booking.timeslot.court.venue.timezone,
                        "allowed_sport_id": booking.timeslot.court.venue.allowed_sport_id,
                    },
                    "sport": {
                        "id": booking.timeslot.court.sport.id,
                        "name": booking.timeslot.court.sport.name,
                        "description": booking.timeslot.court.sport.description,
                    },
                },
            },
        }
    )


@router.get("/policies", response_model=BookingPolicyPublic)
def get_booking_policies():
    return booking_policy_payload()


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
    validate_booking_window(timeslot, now)

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
        existing_booking.updated_at = now
        db.commit()
        db.refresh(existing_booking)
        return existing_booking

    booking = Booking(
        user_id=user_id,
        timeslot_id=timeslot.id,
        status="confirmed",
        created_at=now,
        updated_at=now,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingDetailPublic])
def list_bookings(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    now = datetime.now(timezone.utc)
    bookings = db.execute(
        select(Booking)
        .options(
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.venue),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.sport),
        )
        .where(Booking.user_id == user_id)
        .order_by(Booking.updated_at.desc(), Booking.created_at.desc())
    ).scalars().all()
    return [serialize_booking_detail(booking, db, now) for booking in bookings]


@router.patch("/{booking_id}/cancel", response_model=BookingPublic)
def cancel_booking(booking_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    booking = db.execute(
        select(Booking)
        .options(joinedload(Booking.timeslot))
        .where(
            Booking.id == booking_id,
            Booking.user_id == user_id,
        )
    ).scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail=BOOKING_NOT_FOUND_DETAIL)

    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail=BOOKING_ALREADY_CANCELLED_DETAIL)

    now = datetime.now(timezone.utc)
    if booking.timeslot.starts_at <= now:
        raise HTTPException(status_code=409, detail=BOOKING_EXPIRED_DETAIL)
    if booking.timeslot.starts_at - cancellation_cutoff_delta() <= now:
        raise HTTPException(status_code=409, detail=cancellation_policy_message())

    booking.status = "cancelled"
    booking.updated_at = now
    db.commit()
    db.refresh(booking)
    return booking
