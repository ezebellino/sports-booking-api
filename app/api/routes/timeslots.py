from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.session import get_db
from app.models.timeslot import TimeSlot
from app.models.court import Court
from app.schemas.timeslot import TimeSlotCreate, TimeSlotUpdate, TimeSlotPublic

router = APIRouter(prefix="/timeslots", tags=["timeslots"])

@router.post("", response_model=TimeSlotPublic, status_code=201)
def create_timeslot(payload: TimeSlotCreate, db: Session = Depends(get_db)):
    court = db.get(Court, payload.court_id)
    if not court: raise HTTPException(400, "court_id not found")
    t = TimeSlot(
        court_id=payload.court_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        capacity=payload.capacity,
        price=payload.price,
        is_active=payload.is_active,
    )
    db.add(t); db.commit(); db.refresh(t)
    return t

@router.get("", response_model=list[TimeSlotPublic])
def list_timeslots(
    db: Session = Depends(get_db),
    court_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    qry = db.query(TimeSlot)
    if court_id: qry = qry.filter(TimeSlot.court_id == court_id)
    if date_from: qry = qry.filter(TimeSlot.starts_at >= date_from)
    if date_to: qry = qry.filter(TimeSlot.starts_at < date_to)
    return qry.order_by(TimeSlot.starts_at.asc()).limit(limit).offset(offset).all()

@router.patch("/{timeslot_id}", response_model=TimeSlotPublic)
def update_timeslot(timeslot_id: str, payload: TimeSlotUpdate, db: Session = Depends(get_db)):
    t = db.get(TimeSlot, timeslot_id)
    if not t: raise HTTPException(404, "TimeSlot not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    db.commit(); db.refresh(t)
    return t

@router.delete("/{timeslot_id}", status_code=204)
def delete_timeslot(timeslot_id: str, db: Session = Depends(get_db)):
    t = db.get(TimeSlot, timeslot_id)
    if not t: raise HTTPException(404, "TimeSlot not found")
    db.delete(t); db.commit()
    return
