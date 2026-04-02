from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import require_admin
from app.core.whatsapp import notification_status_payload
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.schemas.admin import AdminMetricsBucket, AdminMetricsPublic, AdminMetricsSummary
from app.schemas.timeslot import TimeSlotBulkCreate, TimeSlotBulkCreateResult, TimeSlotPublic
from app.schemas.user import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])

INACTIVE_COURT_BULK_DETAIL = "No se pueden generar turnos sobre canchas inactivas"


@router.get("/users", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/me", response_model=UserPublic)
def admin_me(current_admin: User = Depends(require_admin)):
    return current_admin


@router.get("/notification-status")
def get_notification_status(_: User = Depends(require_admin)):
    return notification_status_payload()


def _empty_bucket(name: str) -> dict:
    return {
        "name": name,
        "total_timeslots": 0,
        "active_timeslots": 0,
        "confirmed_bookings": 0,
        "cancelled_bookings": 0,
        "spots_total": 0,
        "spots_filled": 0,
        "estimated_revenue": 0.0,
    }


def _finalize_bucket(bucket: dict) -> AdminMetricsBucket:
    booking_events = bucket["confirmed_bookings"] + bucket["cancelled_bookings"]
    occupancy_rate = (bucket["spots_filled"] / bucket["spots_total"] * 100) if bucket["spots_total"] else 0.0
    cancellation_rate = (bucket["cancelled_bookings"] / booking_events * 100) if booking_events else 0.0
    return AdminMetricsBucket(
        name=bucket["name"],
        total_timeslots=bucket["total_timeslots"],
        active_timeslots=bucket["active_timeslots"],
        confirmed_bookings=bucket["confirmed_bookings"],
        cancelled_bookings=bucket["cancelled_bookings"],
        spots_total=bucket["spots_total"],
        spots_filled=bucket["spots_filled"],
        occupancy_rate=round(occupancy_rate, 1),
        cancellation_rate=round(cancellation_rate, 1),
        estimated_revenue=round(bucket["estimated_revenue"], 2),
    )


@router.get("/metrics", response_model=AdminMetricsPublic)
def get_admin_metrics(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stmt = select(TimeSlot).options(
        joinedload(TimeSlot.court).joinedload(Court.sport),
        joinedload(TimeSlot.court).joinedload(Court.venue),
        joinedload(TimeSlot.bookings),
    )

    if date_from is not None:
        stmt = stmt.where(TimeSlot.starts_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(TimeSlot.starts_at <= date_to)

    timeslots = db.execute(stmt.order_by(TimeSlot.starts_at.asc())).unique().scalars().all()
    now = datetime.now(timezone.utc)

    summary = _empty_bucket("summary")
    upcoming_timeslots = 0
    by_sport_data: dict[str, dict] = defaultdict(dict)
    by_venue_data: dict[str, dict] = defaultdict(dict)

    for timeslot in timeslots:
        confirmed_bookings = sum(1 for booking in timeslot.bookings if booking.status == "confirmed")
        cancelled_bookings = sum(1 for booking in timeslot.bookings if booking.status == "cancelled")
        spots_total = timeslot.capacity
        spots_filled = min(confirmed_bookings, spots_total)
        estimated_revenue = float(timeslot.price or 0) * confirmed_bookings
        is_active = bool(timeslot.is_active and timeslot.court.is_active)

        summary["total_timeslots"] += 1
        summary["active_timeslots"] += int(is_active)
        summary["confirmed_bookings"] += confirmed_bookings
        summary["cancelled_bookings"] += cancelled_bookings
        summary["spots_total"] += spots_total
        summary["spots_filled"] += spots_filled
        summary["estimated_revenue"] += estimated_revenue
        if timeslot.starts_at > now:
            upcoming_timeslots += 1

        sport_name = timeslot.court.sport.name
        venue_name = timeslot.court.venue.name

        if sport_name not in by_sport_data:
            by_sport_data[sport_name] = _empty_bucket(sport_name)
        if venue_name not in by_venue_data:
            by_venue_data[venue_name] = _empty_bucket(venue_name)

        for bucket in (by_sport_data[sport_name], by_venue_data[venue_name]):
            bucket["total_timeslots"] += 1
            bucket["active_timeslots"] += int(is_active)
            bucket["confirmed_bookings"] += confirmed_bookings
            bucket["cancelled_bookings"] += cancelled_bookings
            bucket["spots_total"] += spots_total
            bucket["spots_filled"] += spots_filled
            bucket["estimated_revenue"] += estimated_revenue

    booking_events = summary["confirmed_bookings"] + summary["cancelled_bookings"]
    occupancy_rate = (summary["spots_filled"] / summary["spots_total"] * 100) if summary["spots_total"] else 0.0
    cancellation_rate = (summary["cancelled_bookings"] / booking_events * 100) if booking_events else 0.0

    summary_payload = AdminMetricsSummary(
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        total_timeslots=summary["total_timeslots"],
        active_timeslots=summary["active_timeslots"],
        upcoming_timeslots=upcoming_timeslots,
        confirmed_bookings=summary["confirmed_bookings"],
        cancelled_bookings=summary["cancelled_bookings"],
        spots_total=summary["spots_total"],
        spots_filled=summary["spots_filled"],
        occupancy_rate=round(occupancy_rate, 1),
        cancellation_rate=round(cancellation_rate, 1),
        estimated_revenue=round(summary["estimated_revenue"], 2),
    )

    by_sport = sorted((_finalize_bucket(bucket) for bucket in by_sport_data.values()), key=lambda item: (-item.confirmed_bookings, item.name))
    by_venue = sorted((_finalize_bucket(bucket) for bucket in by_venue_data.values()), key=lambda item: (-item.confirmed_bookings, item.name))

    return AdminMetricsPublic(summary=summary_payload, by_sport=by_sport, by_venue=by_venue)


@router.post("/timeslots/bulk", response_model=TimeSlotBulkCreateResult, status_code=201)
def bulk_create_timeslots(
    payload: TimeSlotBulkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    courts = db.query(Court).filter(Court.id.in_(payload.court_ids)).all()
    found_court_ids = {court.id for court in courts}
    missing_court_ids = [str(court_id) for court_id in payload.court_ids if court_id not in found_court_ids]
    if missing_court_ids:
        raise HTTPException(
            status_code=400,
            detail=f"court_id not found: {', '.join(missing_court_ids)}",
        )

    inactive_courts = [court.name for court in courts if not court.is_active and payload.is_active]
    if inactive_courts:
        raise HTTPException(
            status_code=409,
            detail=f"{INACTIVE_COURT_BULK_DETAIL}: {', '.join(inactive_courts)}",
        )

    created_slots: list[TimeSlot] = []
    skipped_reasons: list[str] = []
    step = timedelta(minutes=payload.slot_minutes)

    for court in courts:
        current_start = payload.window_starts_at
        while current_start < payload.window_ends_at:
            current_end = current_start + step

            exists = (
                db.query(TimeSlot)
                .filter(
                    TimeSlot.court_id == court.id,
                    TimeSlot.starts_at == current_start,
                    TimeSlot.ends_at == current_end,
                )
                .first()
            )

            if exists:
                skipped_reasons.append(
                    f"{court.name}: ya existe un turno entre {current_start.isoformat()} y {current_end.isoformat()}"
                )
            else:
                timeslot = TimeSlot(
                    court_id=court.id,
                    starts_at=current_start,
                    ends_at=current_end,
                    capacity=payload.capacity,
                    price=payload.price,
                    is_active=payload.is_active,
                )
                db.add(timeslot)
                created_slots.append(timeslot)

            current_start = current_end

    db.commit()
    for timeslot in created_slots:
        db.refresh(timeslot)

    return TimeSlotBulkCreateResult(
        created_count=len(created_slots),
        skipped_count=len(skipped_reasons),
        created_slots=[TimeSlotPublic.model_validate(timeslot) for timeslot in created_slots],
        skipped_reasons=skipped_reasons,
    )
