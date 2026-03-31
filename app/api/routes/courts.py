from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin
from app.db.session import get_db
from app.models.court import Court
from app.models.sport import Sport
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.models.venue import Venue
from app.schemas.court import CourtCreate, CourtPublic, CourtUpdate

router = APIRouter(prefix="/courts", tags=["courts"])

COURT_NOT_FOUND_DETAIL = "Cancha no encontrada"
VENUE_NOT_FOUND_DETAIL = "Sede no encontrada"
SPORT_NOT_FOUND_DETAIL = "Deporte no encontrado"
COURT_DELETE_BLOCKED_DETAIL = "No se puede eliminar una cancha con turnos asociados"
VENUE_SPORT_MISMATCH_DETAIL = "La sede elegida solo permite otro deporte"


@router.post("", response_model=CourtPublic, status_code=201)
def create_court(
    payload: CourtCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    venue = db.get(Venue, payload.venue_id)
    if not venue:
        raise HTTPException(status_code=400, detail=VENUE_NOT_FOUND_DETAIL)
    if not db.get(Sport, payload.sport_id):
        raise HTTPException(status_code=400, detail=SPORT_NOT_FOUND_DETAIL)
    if venue.allowed_sport_id and venue.allowed_sport_id != payload.sport_id:
        raise HTTPException(status_code=400, detail=VENUE_SPORT_MISMATCH_DETAIL)

    court = Court(
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
    venue_id: str | None = None,
    sport_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(Court)
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
    _: User = Depends(require_admin),
):
    court = db.get(Court, court_id)
    if not court:
        raise HTTPException(status_code=404, detail=COURT_NOT_FOUND_DETAIL)

    next_venue_id = payload.venue_id or court.venue_id
    next_sport_id = payload.sport_id or court.sport_id

    venue = db.get(Venue, next_venue_id)
    if not venue:
        raise HTTPException(status_code=400, detail=VENUE_NOT_FOUND_DETAIL)
    if not db.get(Sport, next_sport_id):
        raise HTTPException(status_code=400, detail=SPORT_NOT_FOUND_DETAIL)
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
    _: User = Depends(require_admin),
):
    court = db.get(Court, court_id)
    if not court:
        raise HTTPException(status_code=404, detail=COURT_NOT_FOUND_DETAIL)
    if court.timeslots:
        raise HTTPException(status_code=409, detail=COURT_DELETE_BLOCKED_DETAIL)

    db.delete(court)
    db.commit()
    return