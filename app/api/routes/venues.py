from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.venue import Venue
from app.models.sport import Sport
from app.schemas.venue import VenueCreate, VenueUpdate, VenuePublic

router = APIRouter(prefix="/venues", tags=["venues"])

@router.post("", response_model=VenuePublic, status_code=201)
def create_venue(payload: VenueCreate, db: Session = Depends(get_db)):
    if payload.allowed_sport_id:
        if not db.get(Sport, payload.allowed_sport_id):
            raise HTTPException(400, "allowed_sport_id not found") # si se provee, debe existir
    v = Venue(
        name=payload.name,
        address=payload.address,
        timezone=payload.timezone,
        allowed_sport_id=payload.allowed_sport_id,  # <-- agregaremos este campo al modelo
    )
    db.add(v); db.commit(); db.refresh(v)
    return v

@router.get("", response_model=list[VenuePublic])
def list_venues(
    db: Session = Depends(get_db),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    qry = db.query(Venue)
    if q:
        qry = qry.filter(Venue.name.ilike(f"%{q}%"))
    return qry.order_by(Venue.name.asc()).limit(limit).offset(offset).all()

@router.patch("/{venue_id}", response_model=VenuePublic)
def update_venue(venue_id: str, payload: VenueUpdate, db: Session = Depends(get_db)):
    v = db.get(Venue, venue_id)
    if not v: raise HTTPException(404, "Venue not found")
    if payload.name is not None: v.name = payload.name
    if payload.address is not None: v.address = payload.address
    if payload.timezone is not None: v.timezone = payload.timezone
    if payload.allowed_sport_id is not None:
        if payload.allowed_sport_id and not db.get(Sport, payload.allowed_sport_id):
            raise HTTPException(400, "allowed_sport_id not found")
        v.allowed_sport_id = payload.allowed_sport_id
    db.commit(); db.refresh(v)
    return v

@router.delete("/{venue_id}", status_code=204)
def delete_venue(venue_id: str, db: Session = Depends(get_db)):
    v = db.get(Venue, venue_id)
    if not v: raise HTTPException(404, "Venue not found")
    db.delete(v); db.commit()
    return
