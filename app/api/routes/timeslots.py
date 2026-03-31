from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.schemas.timeslot import TimeSlotCreate, TimeSlotPublic, TimeSlotUpdate

router = APIRouter(prefix="/timeslots", tags=["timeslots"])


def serialize_timeslot(timeslot: TimeSlot, confirmed_bookings: int) -> TimeSlotPublic:
    remaining_spots = max(timeslot.capacity - confirmed_bookings, 0)
    now = datetime.now(timezone.utc)

    if not timeslot.is_active or not timeslot.court.is_active:
        availability_status = "inactive"
    elif timeslot.ends_at <= now:
        availability_status = "expired"
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
        }
    )


@router.post("", response_model=TimeSlotPublic, status_code=201)
def create_timeslot(
    payload: TimeSlotCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    court = db.get(Court, payload.court_id)
    if not court:
        raise HTTPException(400, "court_id not found")

    timeslot = TimeSlot(
        court_id=payload.court_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        capacity=payload.capacity,
        price=payload.price,
        is_active=payload.is_active,
    )
    db.add(timeslot)
    db.commit()
    db.refresh(timeslot)
    db.refresh(court)
    timeslot.court = court
    return serialize_timeslot(timeslot, confirmed_bookings=0)


@router.get("", response_model=list[TimeSlotPublic])
def list_timeslots(
    db: Session = Depends(get_db),
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
    _: User = Depends(require_admin),
):
    timeslot = db.get(TimeSlot, timeslot_id)
    if not timeslot:
        raise HTTPException(404, "TimeSlot not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(timeslot, field, value)

    db.commit()
    db.refresh(timeslot)

    confirmed_bookings = db.execute(
        select(func.count(Booking.id)).where(
            Booking.timeslot_id == timeslot.id,
            Booking.status == "confirmed",
        )
    ).scalar_one()

    return serialize_timeslot(timeslot, int(confirmed_bookings))


@router.delete("/{timeslot_id}", status_code=204)
def delete_timeslot(
    timeslot_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    timeslot = db.get(TimeSlot, timeslot_id)
    if not timeslot:
        raise HTTPException(404, "TimeSlot not found")

    db.delete(timeslot)
    db.commit()
    return
