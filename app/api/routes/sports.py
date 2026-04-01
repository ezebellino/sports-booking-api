from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin
from app.db.session import get_db
from app.models.sport import Sport
from app.models.user import User
from app.schemas.sport import SportCreate, SportPublic, SportUpdate

router = APIRouter(prefix="/sports", tags=["sports"])

SPORT_NAME_EXISTS_DETAIL = "Ya existe un deporte con ese nombre"
SPORT_NOT_FOUND_DETAIL = "Deporte no encontrado"
EMPTY_SPORT_UPDATE_DETAIL = "No hay cambios para aplicar"


@router.post("", response_model=SportPublic, status_code=201)
def create_sport(
    payload: SportCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    exist = db.query(Sport).filter(Sport.name.ilike(payload.name)).first()
    if exist:
        raise HTTPException(status_code=400, detail=SPORT_NAME_EXISTS_DETAIL)
    sport = Sport(
        name=payload.name,
        description=payload.description,
        booking_min_lead_minutes=payload.booking_min_lead_minutes,
        cancellation_min_lead_minutes=payload.cancellation_min_lead_minutes,
    )
    db.add(sport)
    db.commit()
    db.refresh(sport)
    return sport


@router.get("", response_model=list[SportPublic])
def list_sports(
    db: Session = Depends(get_db),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.query(Sport)
    if q:
        query = query.filter(Sport.name.ilike(f"%{q}%"))
    return query.order_by(Sport.name.asc()).limit(limit).offset(offset).all()


@router.patch("/{sport_id}", response_model=SportPublic)
def update_sport(
    sport_id: UUID,
    payload: SportUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sport = db.get(Sport, sport_id)
    if not sport:
        raise HTTPException(status_code=404, detail=SPORT_NOT_FOUND_DETAIL)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail=EMPTY_SPORT_UPDATE_DETAIL)

    if "name" in data:
        clash = db.query(Sport).filter(Sport.name.ilike(data["name"]), Sport.id != sport_id).first()
        if clash:
            raise HTTPException(status_code=409, detail=SPORT_NAME_EXISTS_DETAIL)
        sport.name = data["name"]

    for field in ("description", "booking_min_lead_minutes", "cancellation_min_lead_minutes"):
        if field in data:
            setattr(sport, field, data[field])

    db.commit()
    db.refresh(sport)
    return sport


@router.get("/{sport_id}", response_model=SportPublic)
def get_sport(sport_id: UUID, db: Session = Depends(get_db)):
    sport = db.get(Sport, sport_id)
    if not sport:
        raise HTTPException(status_code=404, detail=SPORT_NOT_FOUND_DETAIL)
    return sport


@router.put("/{sport_id}", response_model=SportPublic)
def replace_sport(
    sport_id: UUID,
    payload: SportCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sport = db.get(Sport, sport_id)
    if not sport:
        raise HTTPException(status_code=404, detail=SPORT_NOT_FOUND_DETAIL)

    clash = db.query(Sport).filter(Sport.name.ilike(payload.name), Sport.id != sport_id).first()
    if clash:
        raise HTTPException(status_code=409, detail=SPORT_NAME_EXISTS_DETAIL)

    sport.name = payload.name
    sport.description = payload.description
    sport.booking_min_lead_minutes = payload.booking_min_lead_minutes
    sport.cancellation_min_lead_minutes = payload.cancellation_min_lead_minutes
    db.commit()
    db.refresh(sport)
    return sport


@router.delete("/{sport_id}", status_code=204)
def delete_sport(
    sport_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    sport = db.get(Sport, sport_id)
    if not sport:
        raise HTTPException(status_code=404, detail=SPORT_NOT_FOUND_DETAIL)
    db.delete(sport)
    db.commit()
    return
