from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps.auth import (
    require_manage_organization,
    require_manage_staff,
    require_manage_timeslots,
    require_manage_whatsapp,
    require_view_metrics,
)
from app.core.admin_audit import record_admin_audit_event
from app.api.routes.auth import serialize_user
from app.core.holidays import HolidayProviderError, fetch_public_holidays, filter_holidays_by_month
from app.core.organization_settings import get_or_create_organization_settings
from app.core.whatsapp import notification_status_payload
from app.models.admin_audit_event import AdminAuditEvent
from app.models.organization import Organization
from app.models.organization_sport import OrganizationSport
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.models.venue import Venue
from app.schemas.admin import (
    AdminAuditEventPublic,
    AdminReadinessItem,
    AdminReadinessPublic,
    AdminReadinessSummary,
    AdminMetricsBucket,
    AdminMetricsPublic,
    AdminMetricsSummary,
    HolidayCalendarPublic,
    HolidayPublic,
    TenantIntegrityCounts,
    TenantIntegrityIssues,
    TenantIntegrityPublic,
)
from app.schemas.timeslot import TimeSlotBulkCreate, TimeSlotBulkCreateResult, TimeSlotPublic
from app.schemas.user import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])

INACTIVE_COURT_BULK_DETAIL = "No se pueden generar turnos sobre canchas inactivas"


@router.get("/audit-events", response_model=list[AdminAuditEventPublic])
def list_admin_audit_events(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_organization),
):
    events = (
        db.query(AdminAuditEvent)
        .options(joinedload(AdminAuditEvent.actor_user))
        .filter(AdminAuditEvent.organization_id == current_admin.organization_id)
        .order_by(AdminAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AdminAuditEventPublic(
            id=str(event.id),
            action=event.action,
            target_type=event.target_type,
            target_id=event.target_id,
            summary=event.summary,
            actor_email=event.actor_user.email,
            actor_name=event.actor_user.full_name,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]


@router.get("/readiness", response_model=AdminReadinessPublic)
def get_admin_readiness(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_organization),
):
    organization = db.get(Organization, current_admin.organization_id)
    settings = get_or_create_organization_settings(db, organization) if organization else None
    whatsapp_status = notification_status_payload(settings)
    now = datetime.now(timezone.utc)

    enabled_sports_count = int(
        db.execute(
            select(func.count(OrganizationSport.sport_id))
            .where(
                OrganizationSport.organization_id == current_admin.organization_id,
                OrganizationSport.is_enabled.is_(True),
            )
        ).scalar_one()
    )

    venues_count = int(
        db.execute(
            select(func.count(Venue.id)).where(Venue.organization_id == current_admin.organization_id)
        ).scalar_one()
    )
    courts_count = int(
        db.execute(
            select(func.count(Court.id)).where(Court.organization_id == current_admin.organization_id)
        ).scalar_one()
    )
    upcoming_timeslots_count = int(
        db.execute(
            select(func.count(TimeSlot.id)).where(
                TimeSlot.organization_id == current_admin.organization_id,
                TimeSlot.is_active.is_(True),
                TimeSlot.starts_at > now,
            )
        ).scalar_one()
    )

    items = [
        AdminReadinessItem(
            key="branding",
            label="Branding del complejo",
            ready=bool(settings and settings.branding_name and (settings.logo_url or settings.primary_color)),
            detail="Definí nombre de marca y al menos un logo o color principal visible.",
        ),
        AdminReadinessItem(
            key="booking_policy",
            label="Política general",
            ready=bool(
                settings
                and settings.booking_min_lead_minutes is not None
                and settings.cancellation_min_lead_minutes is not None
            ),
            detail="Configurá anticipación mínima para reservar y cancelar.",
        ),
        AdminReadinessItem(
            key="whatsapp",
            label="WhatsApp operativo",
            ready=bool(whatsapp_status["ready_for_live_send"]),
            detail="Cargá proveedor, credenciales y templates para enviar mensajes reales.",
        ),
        AdminReadinessItem(
            key="sports",
            label="Deportes habilitados",
            ready=enabled_sports_count > 0,
            detail="Habilitá al menos un deporte para que el complejo tenga oferta visible.",
        ),
        AdminReadinessItem(
            key="venues",
            label="Sedes cargadas",
            ready=venues_count > 0,
            detail="Creá al menos una sede operativa.",
        ),
        AdminReadinessItem(
            key="courts",
            label="Canchas cargadas",
            ready=courts_count > 0,
            detail="Creá al menos una cancha o recurso reservable.",
        ),
        AdminReadinessItem(
            key="upcoming_timeslots",
            label="Turnos futuros publicados",
            ready=upcoming_timeslots_count > 0,
            detail="Publicá al menos un turno futuro para que el usuario pueda reservar.",
        ),
    ]

    completed_items = sum(1 for item in items if item.ready)
    total_items = len(items)
    missing_items = [item.label for item in items if not item.ready]

    return AdminReadinessPublic(
        summary=AdminReadinessSummary(
            is_ready=completed_items == total_items,
            completed_items=completed_items,
            total_items=total_items,
            readiness_percent=round(completed_items / total_items * 100) if total_items else 0,
            missing_items=missing_items,
        ),
        items=items,
    )


@router.get("/users", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_manage_staff)):
    current_admin = _
    users = (
        db.query(User)
        .filter(User.organization_id == current_admin.organization_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [serialize_user(user) for user in users]


@router.get("/me", response_model=UserPublic)
def admin_me(current_admin: User = Depends(require_manage_staff)):
    return serialize_user(current_admin)


@router.get("/notification-status")
def get_notification_status(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_whatsapp),
):
    organization = current_admin.organization
    settings = get_or_create_organization_settings(db, organization) if organization else None
    return notification_status_payload(settings)


@router.get("/holidays", response_model=HolidayCalendarPublic)
def get_holidays_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    country_code: str = Query(default="AR", min_length=2, max_length=2),
    _: User = Depends(require_manage_timeslots),
):
    try:
        holidays = filter_holidays_by_month(fetch_public_holidays(year, country_code), month)
    except HolidayProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return HolidayCalendarPublic(
        country_code=country_code.strip().upper(),
        year=year,
        month=month,
        holidays=[
            HolidayPublic(
                date=holiday.date,
                local_name=holiday.local_name,
                name=holiday.name,
                country_code=holiday.country_code,
                global_holiday=holiday.global_holiday,
                counties=holiday.counties,
                launch_year=holiday.launch_year,
                types=holiday.types,
            )
            for holiday in holidays
        ],
    )


@router.get("/tenant-integrity", response_model=TenantIntegrityPublic)
def get_tenant_integrity(
    db: Session = Depends(get_db),
    _: User = Depends(require_manage_organization),
):
    counts = TenantIntegrityCounts(
        organizations=int(db.execute(select(func.count(Organization.id))).scalar_one()),
        users_without_organization=int(
            db.execute(select(func.count(User.id)).where(User.organization_id.is_(None))).scalar_one()
        ),
        venues_without_organization=int(
            db.execute(select(func.count(Venue.id)).where(Venue.organization_id.is_(None))).scalar_one()
        ),
        courts_without_organization=int(
            db.execute(select(func.count(Court.id)).where(Court.organization_id.is_(None))).scalar_one()
        ),
        timeslots_without_organization=int(
            db.execute(select(func.count(TimeSlot.id)).where(TimeSlot.organization_id.is_(None))).scalar_one()
        ),
        bookings_without_organization=int(
            db.execute(select(func.count(Booking.id)).where(Booking.organization_id.is_(None))).scalar_one()
        ),
    )

    issues = TenantIntegrityIssues(
        court_venue_mismatches=int(
            db.execute(
                select(func.count(Court.id))
                .join(Venue, Venue.id == Court.venue_id)
                .where(Court.organization_id.is_not(None), Venue.organization_id.is_not(None))
                .where(Court.organization_id != Venue.organization_id)
            ).scalar_one()
        ),
        timeslot_court_mismatches=int(
            db.execute(
                select(func.count(TimeSlot.id))
                .join(Court, Court.id == TimeSlot.court_id)
                .where(TimeSlot.organization_id.is_not(None), Court.organization_id.is_not(None))
                .where(TimeSlot.organization_id != Court.organization_id)
            ).scalar_one()
        ),
        booking_user_mismatches=int(
            db.execute(
                select(func.count(Booking.id))
                .join(User, User.id == Booking.user_id)
                .where(Booking.organization_id.is_not(None), User.organization_id.is_not(None))
                .where(Booking.organization_id != User.organization_id)
            ).scalar_one()
        ),
        booking_timeslot_mismatches=int(
            db.execute(
                select(func.count(Booking.id))
                .join(TimeSlot, TimeSlot.id == Booking.timeslot_id)
                .where(Booking.organization_id.is_not(None), TimeSlot.organization_id.is_not(None))
                .where(Booking.organization_id != TimeSlot.organization_id)
            ).scalar_one()
        ),
    )

    ready_for_not_null = (
        counts.users_without_organization == 0
        and counts.venues_without_organization == 0
        and counts.courts_without_organization == 0
        and counts.timeslots_without_organization == 0
        and counts.bookings_without_organization == 0
        and issues.court_venue_mismatches == 0
        and issues.timeslot_court_mismatches == 0
        and issues.booking_user_mismatches == 0
        and issues.booking_timeslot_mismatches == 0
    )

    return TenantIntegrityPublic(
        counts=counts,
        issues=issues,
        ready_for_not_null=ready_for_not_null,
    )


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
    current_admin: User = Depends(require_view_metrics),
):
    stmt = select(TimeSlot).options(
        joinedload(TimeSlot.court).joinedload(Court.sport),
        joinedload(TimeSlot.court).joinedload(Court.venue),
        joinedload(TimeSlot.bookings),
    )
    stmt = stmt.where(TimeSlot.organization_id == current_admin.organization_id)

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
    current_admin: User = Depends(require_manage_timeslots),
):
    courts = (
        db.query(Court)
        .filter(Court.id.in_(payload.court_ids), Court.organization_id == current_admin.organization_id)
        .all()
    )
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
                    organization_id=current_admin.organization_id,
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

    record_admin_audit_event(
        db,
        organization_id=current_admin.organization_id,
        actor_user_id=current_admin.id,
        action="timeslots.bulk_created",
        target_type="timeslot",
        summary=f"Generó {len(created_slots)} turnos masivos en {len(courts)} canchas.",
        details={
            "created_count": len(created_slots),
            "skipped_count": len(skipped_reasons),
            "court_ids": [str(court.id) for court in courts],
        },
    )
    db.commit()

    return TimeSlotBulkCreateResult(
        created_count=len(created_slots),
        skipped_count=len(skipped_reasons),
        created_slots=[TimeSlotPublic.model_validate(timeslot) for timeslot in created_slots],
        skipped_reasons=skipped_reasons,
    )
