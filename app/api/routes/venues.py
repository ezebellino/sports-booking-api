from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import get_request_organization, require_admin
from app.db.session import get_db
from app.models.organization import Organization
from app.models.sport import Sport
from app.models.venue import Venue
from app.models.user import User
from app.schemas.venue import VenueCreate, VenuePublic, VenueUpdate

router = APIRouter(prefix="/venues", tags=["venues"])

VENUE_NOT_FOUND_DETAIL = "Sede no encontrada"
SPORT_NOT_FOUND_DETAIL = "Deporte no encontrado"
VENUE_DELETE_BLOCKED_DETAIL = "No se puede eliminar una sede con canchas asociadas"


@router.post("", response_model=VenuePublic, status_code=201)
def create_venue(
    payload: VenueCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    if payload.allowed_sport_id and not db.get(Sport, payload.allowed_sport_id):
        raise HTTPException(status_code=400, detail=SPORT_NOT_FOUND_DETAIL)

    venue = Venue(
        organization_id=current_admin.organization_id,
        name=payload.name,
        address=payload.address,
        timezone=payload.timezone,
        allowed_sport_id=payload.allowed_sport_id,
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


@router.get("", response_model=list[VenuePublic])
def list_venues(
    db: Session = Depends(get_db),
    organization: Organization = Depends(get_request_organization),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(Venue).filter(Venue.organization_id == organization.id)
    if q:
        query = query.filter(Venue.name.ilike(f"%{q}%"))
    return query.order_by(Venue.name.asc()).limit(limit).offset(offset).all()


@router.patch("/{venue_id}", response_model=VenuePublic)
def update_venue(
    venue_id: str,
    payload: VenueUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    venue = db.query(Venue).filter(Venue.id == venue_id, Venue.organization_id == current_admin.organization_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail=VENUE_NOT_FOUND_DETAIL)

    if payload.allowed_sport_id is not None and payload.allowed_sport_id and not db.get(Sport, payload.allowed_sport_id):
        raise HTTPException(status_code=400, detail=SPORT_NOT_FOUND_DETAIL)

    if payload.name is not None:
        venue.name = payload.name
    if payload.address is not None:
        venue.address = payload.address
    if payload.timezone is not None:
        venue.timezone = payload.timezone
    if payload.allowed_sport_id is not None:
        venue.allowed_sport_id = payload.allowed_sport_id

    db.commit()
    db.refresh(venue)
    return venue


@router.delete("/{venue_id}", status_code=204)
def delete_venue(
    venue_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    venue = db.query(Venue).filter(Venue.id == venue_id, Venue.organization_id == current_admin.organization_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail=VENUE_NOT_FOUND_DETAIL)
    if venue.courts:
        raise HTTPException(status_code=409, detail=VENUE_DELETE_BLOCKED_DETAIL)

    db.delete(venue)
    db.commit()
    return
