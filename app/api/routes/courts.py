from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.court import Court
from app.models.venue import Venue
from app.models.sport import Sport
from app.schemas.court import CourtCreate, CourtUpdate, CourtPublic

router = APIRouter(prefix="/courts", tags=["courts"])

@router.post("", response_model=CourtPublic, status_code=201)
def create_court(payload: CourtCreate, db: Session = Depends(get_db)):
    venue = db.get(Venue, payload.venue_id)
    if not venue: raise HTTPException(400, "venue_id not found")
    if not db.get(Sport, payload.sport_id): raise HTTPException(400, "sport_id not found")
    # Si el venue es mono-deporte, el sport_id debe coincidir
    if getattr(venue, "allowed_sport_id", None) and venue.allowed_sport_id != payload.sport_id:
        raise HTTPException(400, "This venue only allows one sport")
    c = Court(
        venue_id=payload.venue_id,
        sport_id=payload.sport_id,
        name=payload.name,
        indoor=payload.indoor,
        is_active=payload.is_active,
    )
    db.add(c); db.commit(); db.refresh(c)
    return c

@router.get("", response_model=list[CourtPublic])
def list_courts(
    db: Session = Depends(get_db),
    venue_id: str | None = None,
    sport_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    qry = db.query(Court)
    if venue_id: qry = qry.filter(Court.venue_id == venue_id)
    if sport_id: qry = qry.filter(Court.sport_id == sport_id)
    return qry.order_by(Court.name.asc()).limit(limit).offset(offset).all()

@router.patch("/{court_id}", response_model=CourtPublic)
def update_court(court_id: str, payload: CourtUpdate, db: Session = Depends(get_db)):
    c = db.get(Court, court_id)
    if not c: raise HTTPException(404, "Court not found")
    if payload.name is not None: c.name = payload.name
    if payload.indoor is not None: c.indoor = payload.indoor
    if payload.is_active is not None: c.is_active = payload.is_active
    db.commit(); db.refresh(c)
    return c

@router.delete("/{court_id}", status_code=204)
def delete_court(court_id: str, db: Session = Depends(get_db)):
    c = db.get(Court, court_id)
    if not c: raise HTTPException(404, "Court not found")
    db.delete(c); db.commit()
    return
