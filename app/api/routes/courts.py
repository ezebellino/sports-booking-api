from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_request_organization, require_manage_inventory
from app.db.session import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.organization import Organization
from app.models.organization_sport import OrganizationSport
from app.models.sport import Sport
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.models.venue import Venue
from app.schemas.court import CourtCreate, CourtPublic, CourtUpdate

router = APIRouter(prefix="/courts", tags=["courts"])

COURT_NOT_FOUND_DETAIL = "Cancha no encontrada"
VENUE_NOT_FOUND_DETAIL = "Sede no encontrada"
SPORT_NOT_FOUND_DETAIL = "Deporte no encontrado"
SPORT_NOT_ENABLED_DETAIL = "El deporte no está habilitado para este complejo"
COURT_DELETE_BLOCKED_FUTURE_TIMESLOTS_DETAIL = "No se puede eliminar una cancha con turnos futuros asociados"
COURT_DELETE_BLOCKED_BOOKINGS_DETAIL = "No se puede eliminar una cancha con reservas asociadas"
VENUE_SPORT_MISMATCH_DETAIL = "La sede elegida solo permite otro deporte"


def ensure_enabled_organization_sport(db: Session, organization_id, sport_id):
    enabled = db.query(OrganizationSport).filter(
        OrganizationSport.organization_id == organization_id,
        OrganizationSport.sport_id == sport_id,
        OrganizationSport.is_enabled.is_(True),
    ).first()
    if enabled:
        return enabled

    any_row_for_sport = db.query(OrganizationSport).filter(OrganizationSport.sport_id == sport_id).first()
    if any_row_for_sport:
        return None

    enabled = OrganizationSport(
        organization_id=organization_id,
        sport_id=sport_id,
        is_enabled=True,
    )
    db.add(enabled)
    db.flush()
    return enabled


@router.post("", response_model=CourtPublic, status_code=201)
def create_court(
    payload: CourtCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_inventory),
):
    venue = db.query(Venue).filter(Venue.id == payload.venue_id, Venue.organization_id == current_admin.organization_id).first()
    if not venue:
        raise HTTPException(status_code=400, detail=VENUE_NOT_FOUND_DETAIL)
    if not db.get(Sport, payload.sport_id):
        raise HTTPException(status_code=400, detail=SPORT_NOT_FOUND_DETAIL)
    enabled = ensure_enabled_organization_sport(
        db,
        current_admin.organization_id,
        payload.sport_id,
    )
    if not enabled:
        raise HTTPException(status_code=400, detail=SPORT_NOT_ENABLED_DETAIL)
    if venue.allowed_sport_id and venue.allowed_sport_id != payload.sport_id:
        raise HTTPException(status_code=400, detail=VENUE_SPORT_MISMATCH_DETAIL)

    court = Court(
        organization_id=current_admin.organization_id,
        venue_id=payload.venue_id,
        sport_id=payload.sport_id,
        name=payload.name,
        indoor=payload.indoor,
        is_active=payload.is_active,
    )
    db.add(court)
    db.commit()
    db.refresh(court)
    return court


@router.get("", response_model=list[CourtPublic])
def list_courts(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_request_organization),
    venue_id: str | None = None,
    sport_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(Court).filter(Court.organization_id == organization.id)
    if venue_id:
        query = query.filter(Court.venue_id == venue_id)
    if sport_id:
        query = query.filter(Court.sport_id == sport_id)
    return query.order_by(Court.name.asc()).limit(limit).offset(offset).all()


@router.patch("/{court_id}", response_model=CourtPublic)
def update_court(
    court_id: str,
    payload: CourtUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_inventory),
):
    court = db.query(Court).filter(Court.id == court_id, Court.organization_id == current_admin.organization_id).first()
    if not court:
        raise HTTPException(status_code=404, detail=COURT_NOT_FOUND_DETAIL)

    next_venue_id = payload.venue_id or court.venue_id
    next_sport_id = payload.sport_id or court.sport_id

    venue = db.query(Venue).filter(Venue.id == next_venue_id, Venue.organization_id == current_admin.organization_id).first()
    if not venue:
        raise HTTPException(status_code=400, detail=VENUE_NOT_FOUND_DETAIL)
    if not db.get(Sport, next_sport_id):
        raise HTTPException(status_code=400, detail=SPORT_NOT_FOUND_DETAIL)
    enabled = ensure_enabled_organization_sport(
        db,
        current_admin.organization_id,
        next_sport_id,
    )
    if not enabled:
        raise HTTPException(status_code=400, detail=SPORT_NOT_ENABLED_DETAIL)
    if venue.allowed_sport_id and venue.allowed_sport_id != next_sport_id:
        raise HTTPException(status_code=400, detail=VENUE_SPORT_MISMATCH_DETAIL)

    if payload.venue_id is not None:
        court.venue_id = payload.venue_id
    if payload.sport_id is not None:
        court.sport_id = payload.sport_id
    if payload.name is not None:
        court.name = payload.name
    if payload.indoor is not None:
        court.indoor = payload.indoor
    if payload.is_active is not None:
        court.is_active = payload.is_active

    db.commit()
    db.refresh(court)
    return court


@router.delete("/{court_id}", status_code=204)
def delete_court(
    court_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_manage_inventory),
):
    now = datetime.now(timezone.utc)
    court = db.query(Court).filter(Court.id == court_id, Court.organization_id == current_admin.organization_id).first()
    if not court:
        raise HTTPException(status_code=404, detail=COURT_NOT_FOUND_DETAIL)

    has_bookings = (
        db.query(Booking.id)
        .join(TimeSlot, TimeSlot.id == Booking.timeslot_id)
        .filter(TimeSlot.court_id == court.id)
        .first()
    )
    if has_bookings:
        raise HTTPException(status_code=409, detail=COURT_DELETE_BLOCKED_BOOKINGS_DETAIL)

    has_future_timeslots = (
        db.query(TimeSlot.id)
        .filter(TimeSlot.court_id == court.id, TimeSlot.starts_at >= now)
        .first()
    )
    if has_future_timeslots:
        raise HTTPException(status_code=409, detail=COURT_DELETE_BLOCKED_FUTURE_TIMESLOTS_DETAIL)

    db.delete(court)
    db.commit()
    return
