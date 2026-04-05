from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import AUTH_ERROR_DETAIL, get_request_organization
from app.api.routes.auth import oauth2_scheme
from app.core.booking_policy import (
    booking_policy_message,
    cancellation_policy_message,
    policy_source_message,
    resolve_policy_for_sport,
    resolve_policy_for_timeslot,
)
from app.core.notifications import (
    send_booking_cancelled_notification,
    send_booking_confirmed_notification,
)
from app.core.security import decode_token
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.organization import Organization
from app.models.sport import Sport
from app.models.timeslot import TimeSlot
from app.models.user import User
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


def count_confirmed_bookings(db: Session, timeslot_id: UUID) -> int:
    return int(
        db.execute(
            select(func.count(Booking.id)).where(
                Booking.timeslot_id == timeslot_id,
                Booking.status == "confirmed",
            )
        ).scalar_one()
    )


def booking_policy_payload(sport: Sport | None = None, organization_settings=None) -> BookingPolicyPublic:
    policy = resolve_policy_for_sport(sport, organization_settings)
    return BookingPolicyPublic(
        sport_id=policy.sport_id,
        sport_name=policy.sport_name,
        uses_default_policy=policy.uses_default_policy,
        min_booking_lead_minutes=policy.min_booking_lead_minutes,
        cancellation_min_lead_minutes=policy.cancellation_min_lead_minutes,
        booking_message=booking_policy_message(policy),
        cancellation_message=cancellation_policy_message(policy),
        admin_summary=policy_source_message(policy),
    )


def validate_booking_window(timeslot: TimeSlot, now: datetime) -> None:
    policy = resolve_policy_for_timeslot(timeslot)
    if timeslot.starts_at <= now:
        raise HTTPException(status_code=409, detail=BOOKING_EXPIRED_DETAIL)
    if timeslot.starts_at < now + timedelta(minutes=policy.min_booking_lead_minutes):
        raise HTTPException(status_code=409, detail=booking_policy_message(policy))


def derive_availability_status(timeslot: TimeSlot, confirmed_bookings: int, now: datetime) -> str:
    remaining_spots = max(timeslot.capacity - confirmed_bookings, 0)
    policy = resolve_policy_for_timeslot(timeslot)

    if not timeslot.is_active or not timeslot.court.is_active:
        return "inactive"
    if timeslot.starts_at <= now:
        return "expired"
    if timeslot.starts_at < now + timedelta(minutes=policy.min_booking_lead_minutes):
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
    policy = resolve_policy_for_timeslot(booking.timeslot)
    cancellation_deadline = booking.timeslot.starts_at - timedelta(minutes=policy.cancellation_min_lead_minutes)
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
            "cancellation_policy_message": cancellation_policy_message(policy),
            "booking_policy_summary": policy_source_message(policy),
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
                "policy_summary": policy_source_message(policy),
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
                        "booking_min_lead_minutes": booking.timeslot.court.sport.booking_min_lead_minutes,
                        "cancellation_min_lead_minutes": booking.timeslot.court.sport.cancellation_min_lead_minutes,
                    },
                },
            },
        }
    )


@router.get("/policies", response_model=BookingPolicyPublic)
def get_booking_policies(
    sport_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    organization = Depends(get_request_organization),
):
    sport = db.get(Sport, sport_id) if sport_id else None
    if sport_id and sport is None:
        raise HTTPException(status_code=404, detail="Deporte no encontrado")
    return booking_policy_payload(sport, organization.settings if organization else None)


@router.post("", response_model=BookingPublic, status_code=201)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    timeslot = db.execute(
        select(TimeSlot)
        .options(
            joinedload(TimeSlot.organization).joinedload(Organization.settings),
            joinedload(TimeSlot.court).joinedload(Court.sport),
            joinedload(TimeSlot.court).joinedload(Court.venue),
        )
        .where(TimeSlot.id == payload.timeslot_id, TimeSlot.organization_id == user.organization_id)
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
        booking = db.execute(
            select(Booking)
            .options(
                joinedload(Booking.organization).joinedload(Organization.settings),
                joinedload(Booking.user),
                joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.venue),
                joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.sport),
            )
            .where(Booking.id == existing_booking.id)
        ).scalar_one()
        send_booking_confirmed_notification(booking)
        return booking

    booking = Booking(
        user_id=user_id,
        organization_id=user.organization_id,
        timeslot_id=timeslot.id,
        status="confirmed",
        created_at=now,
        updated_at=now,
    )
    db.add(booking)
    db.commit()
    booking = db.execute(
        select(Booking)
        .options(
            joinedload(Booking.organization).joinedload(Organization.settings),
            joinedload(Booking.user),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.venue),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.sport),
        )
        .where(Booking.id == booking.id)
    ).scalar_one()
    send_booking_confirmed_notification(booking)
    return booking


@router.get("", response_model=list[BookingDetailPublic])
def list_bookings(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    now = datetime.now(timezone.utc)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    bookings = db.execute(
        select(Booking)
        .options(
            joinedload(Booking.organization).joinedload(Organization.settings),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.venue),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.sport),
        )
        .where(Booking.user_id == user_id, Booking.organization_id == user.organization_id)
        .order_by(Booking.updated_at.desc(), Booking.created_at.desc())
    ).scalars().all()
    return [serialize_booking_detail(booking, db, now) for booking in bookings]


@router.patch("/{booking_id}/cancel", response_model=BookingPublic)
def cancel_booking(booking_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    booking = db.execute(
        select(Booking)
        .options(
            joinedload(Booking.organization).joinedload(Organization.settings),
            joinedload(Booking.user),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.sport),
            joinedload(Booking.timeslot).joinedload(TimeSlot.court).joinedload(Court.venue),
        )
        .where(
            Booking.id == booking_id,
            Booking.user_id == user_id,
            Booking.organization_id == user.organization_id,
        )
    ).scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail=BOOKING_NOT_FOUND_DETAIL)

    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail=BOOKING_ALREADY_CANCELLED_DETAIL)

    policy = resolve_policy_for_timeslot(booking.timeslot)
    now = datetime.now(timezone.utc)
    if booking.timeslot.starts_at <= now:
        raise HTTPException(status_code=409, detail=BOOKING_EXPIRED_DETAIL)
    if booking.timeslot.starts_at - timedelta(minutes=policy.cancellation_min_lead_minutes) <= now:
        raise HTTPException(status_code=409, detail=cancellation_policy_message(policy))

    booking.status = "cancelled"
    booking.updated_at = now
    db.commit()
    db.refresh(booking)
    send_booking_cancelled_notification(booking)
    return booking
