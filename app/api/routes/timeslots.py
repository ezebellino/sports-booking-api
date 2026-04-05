from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import get_request_organization, require_manage_timeslots
from app.core.admin_audit import record_admin_audit_event
from app.core.booking_policy import policy_source_message, resolve_policy_for_timeslot
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.organization import Organization
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.schemas.timeslot import TimeSlotCreate, TimeSlotPublic, TimeSlotUpdate

router = APIRouter(prefix="/timeslots", tags=["timeslots"])

COURT_NOT_FOUND_DETAIL = "Cancha no encontrada"
INACTIVE_COURT_TIMESLOT_DETAIL = "No se pueden crear o activar turnos sobre una cancha inactiva"
TIMESLOT_NOT_FOUND_DETAIL = "Turno no encontrado"
TIMESLOT_CAPACITY_CONFLICT_DETAIL = "La capacidad no puede quedar por debajo de las reservas confirmadas"


def booking_cutoff_delta(timeslot: TimeSlot) -> timedelta:
    policy = resolve_policy_for_timeslot(timeslot)
    return timedelta(minutes=policy.min_booking_lead_minutes)


def serialize_timeslot(timeslot: TimeSlot, confirmed_bookings: int) -> TimeSlotPublic:
    remaining_spots = max(timeslot.capacity - confirmed_bookings, 0)
    now = datetime.now(timezone.utc)

    if not timeslot.is_active or not timeslot.court.is_active:
        availability_status = "inactive"
    elif timeslot.starts_at <= now:
        availability_status = "expired"
    elif timeslot.starts_at < now + booking_cutoff_delta(timeslot):
        availability_status = "booking_closed"
    elif remaining_spots <= 0:
        availability_status = "full"
    elif remaining_spots == 1:
        availability_status = "few_left"
    else:
        availability_status = "available"

    return TimeSlotPublic.model_validate(
        {
            "id": timeslot.id,
            "court_id": timeslot.court_id,
            "starts_at": timeslot.starts_at,
            "ends_at": timeslot.ends_at,
            "capacity": timeslot.capacity,
            "price": timeslot.price,
            "is_active": timeslot.is_active,
            "confirmed_bookings": confirmed_bookings,
            "remaining_spots": remaining_spots,
            "availability_status": availability_status,
            "policy_summary": policy_source_message(resolve_policy_for_timeslot(timeslot)),
        }
    )


def count_confirmed_bookings(db: Session, timeslot_id) -> int:
    return int(
        db.execute(
            select(func.count(Booking.id)).where(
                Booking.timeslot_id == timeslot_id,
                Booking.status == "confirmed",
            )
        ).scalar_one()
    )


@router.post("", response_model=TimeSlotPublic, status_code=201)
def create_timeslot(
    payload: TimeSlotCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_timeslots),
):
    court = db.execute(
        select(Court)
        .options(joinedload(Court.sport))
        .where(Court.id == payload.court_id, Court.organization_id == current_admin.organization_id)
    ).scalar_one_or_none()
    if not court:
        raise HTTPException(status_code=400, detail=COURT_NOT_FOUND_DETAIL)
    if not court.is_active and payload.is_active:
        raise HTTPException(status_code=409, detail=INACTIVE_COURT_TIMESLOT_DETAIL)

    timeslot = TimeSlot(
        organization_id=current_admin.organization_id,
        court_id=payload.court_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        capacity=payload.capacity,
        price=payload.price,
        is_active=payload.is_active,
    )
    db.add(timeslot)
    db.flush()
    record_admin_audit_event(
        db,
        organization_id=current_admin.organization_id,
        actor_user_id=current_admin.id,
        action="timeslot.created",
        target_type="timeslot",
        target_id=str(timeslot.id),
        summary=f"Creó un turno en {court.name}.",
        details={"court_id": str(court.id), "starts_at": payload.starts_at.isoformat()},
    )
    db.commit()
    db.refresh(timeslot)
    db.refresh(court)
    timeslot.court = court
    return serialize_timeslot(timeslot, confirmed_bookings=0)


@router.get("", response_model=list[TimeSlotPublic])
def list_timeslots(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_request_organization),
    court_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    confirmed_bookings_subquery = (
        select(
            Booking.timeslot_id.label("timeslot_id"),
            func.count(Booking.id).label("confirmed_bookings"),
        )
        .where(Booking.status == "confirmed")
        .group_by(Booking.timeslot_id)
        .subquery()
    )

    query = (
        db.query(TimeSlot, func.coalesce(confirmed_bookings_subquery.c.confirmed_bookings, 0).label("confirmed_bookings"))
        .join(Court, Court.id == TimeSlot.court_id)
        .outerjoin(confirmed_bookings_subquery, confirmed_bookings_subquery.c.timeslot_id == TimeSlot.id)
        .options(joinedload(TimeSlot.organization).joinedload(Organization.settings))
        .options(joinedload(TimeSlot.court).joinedload(Court.sport))
        .filter(TimeSlot.organization_id == organization.id)
    )

    if court_id:
        query = query.filter(TimeSlot.court_id == court_id)
    if date_from:
        query = query.filter(TimeSlot.starts_at >= date_from)
    if date_to:
        query = query.filter(TimeSlot.starts_at < date_to)

    rows = query.order_by(TimeSlot.starts_at.asc()).limit(limit).offset(offset).all()
    return [serialize_timeslot(timeslot, int(confirmed_bookings)) for timeslot, confirmed_bookings in rows]


@router.patch("/{timeslot_id}", response_model=TimeSlotPublic)
def update_timeslot(
    timeslot_id: str,
    payload: TimeSlotUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_timeslots),
):
    timeslot = db.execute(
        select(TimeSlot)
        .options(joinedload(TimeSlot.organization).joinedload(Organization.settings))
        .options(joinedload(TimeSlot.court).joinedload(Court.sport))
        .where(TimeSlot.id == timeslot_id, TimeSlot.organization_id == current_admin.organization_id)
    ).scalar_one_or_none()
    if not timeslot:
        raise HTTPException(status_code=404, detail=TIMESLOT_NOT_FOUND_DETAIL)

    confirmed_bookings = count_confirmed_bookings(db, timeslot.id)
    next_capacity = payload.capacity if payload.capacity is not None else timeslot.capacity
    next_is_active = payload.is_active if payload.is_active is not None else timeslot.is_active

    if next_capacity < confirmed_bookings:
        raise HTTPException(status_code=409, detail=TIMESLOT_CAPACITY_CONFLICT_DETAIL)
    if not timeslot.court.is_active and next_is_active:
        raise HTTPException(status_code=409, detail=INACTIVE_COURT_TIMESLOT_DETAIL)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(timeslot, field, value)

    record_admin_audit_event(
        db,
        organization_id=current_admin.organization_id,
        actor_user_id=current_admin.id,
        action="timeslot.updated",
        target_type="timeslot",
        target_id=str(timeslot.id),
        summary=f"Actualizó un turno de {timeslot.court.name}.",
        details={"court_id": str(timeslot.court.id), "starts_at": timeslot.starts_at.isoformat()},
    )
    db.commit()
    db.refresh(timeslot)
    return serialize_timeslot(timeslot, confirmed_bookings)


@router.delete("/{timeslot_id}", status_code=204)
def delete_timeslot(
    timeslot_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_timeslots),
):
    timeslot = db.query(TimeSlot).filter(TimeSlot.id == timeslot_id, TimeSlot.organization_id == current_admin.organization_id).first()
    if not timeslot:
        raise HTTPException(status_code=404, detail=TIMESLOT_NOT_FOUND_DETAIL)

    record_admin_audit_event(
        db,
        organization_id=current_admin.organization_id,
        actor_user_id=current_admin.id,
        action="timeslot.deleted",
        target_type="timeslot",
        target_id=str(timeslot.id),
        summary=f"Eliminó un turno de {timeslot.court.name}.",
        details={"court_id": str(timeslot.court_id), "starts_at": timeslot.starts_at.isoformat()},
    )
    db.delete(timeslot)
    db.commit()
    return
