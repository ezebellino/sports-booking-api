from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.sport import Sport
from app.schemas.sport import SportCreate, SportUpdate, SportPublic

router = APIRouter(prefix="/sports", tags=["sports"])

@router.post("", response_model=SportPublic, status_code=201)
def create_sport(payload: SportCreate, db: Session = Depends(get_db)):
    exist = db.query(Sport).filter(Sport.name.ilike(payload.name)).first()
    if exist:
        raise HTTPException(status_code=400, detail="Sport name already exists")
    s = Sport(name=payload.name, description=payload.description)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.get("", response_model=list[SportPublic])
def list_sports(
    db: Session = Depends(get_db),
    q : str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    qry = db.query(Sport)
    if q:
        qry = qry.filter(Sport.name.ilike(f"%{q}%")) # búsqueda case insensitive
    return qry.order_by(Sport.name.asc()).limit(limit).offset(offset).all() # devuelve una lista en orden alfabético

@router.patch("/{sport_id}", response_model=SportPublic)
def update_sport(sport_id: UUID, payload: SportUpdate, db: Session = Depends(get_db)):
    s = db.get(Sport, sport_id)
    if not s:
        raise HTTPException(404, "Sport not found")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(400, "Empty update payload")
    if "name" in data:
        clash = db.query(Sport).filter(Sport.name.ilike(data["name"]), Sport.id != sport_id).first()
        if clash:
            raise HTTPException(409, "Sport name already exists")
        s.name = data["name"]
    if "description" in data:
        s.description = data["description"]
    db.commit(); db.refresh(s)
    return s

@router.get("/{sport_id}", response_model=SportPublic)
def get_sport(sport_id: UUID, db: Session = Depends(get_db)):
    s = db.get(Sport, sport_id)
    if not s:
        raise HTTPException(404, "Sport not found")
    return s

@router.put("/{sport_id}", response_model=SportPublic)
def replace_sport(sport_id: UUID, payload: SportCreate, db: Session = Depends(get_db)):
    s = db.get(Sport, sport_id)
    if not s:
        raise HTTPException(404, "Sport not found")
    # validación de nombre único
    clash = db.query(Sport).filter(Sport.name.ilike(payload.name), Sport.id != sport_id).first()
    if clash:
        raise HTTPException(409, "Sport name already exists")
    s.name = payload.name
    s.description = payload.description
    db.commit(); db.refresh(s)
    return s

@router.delete("/{sport_id}", status_code=204)
def delete_sport(sport_id: str, db: Session = Depends(get_db)):
    s = db.get(Sport, sport_id)
    if not s: raise HTTPException(404, "Sport not found")
    db.delete(s)
    db.commit()
    return 