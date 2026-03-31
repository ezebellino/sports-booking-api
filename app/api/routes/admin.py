from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps.auth import require_admin
from app.db.session import get_db
from app.models.court import Court
from app.models.timeslot import TimeSlot
from app.models.user import User
from app.schemas.timeslot import TimeSlotBulkCreate, TimeSlotBulkCreateResult, TimeSlotPublic
from app.schemas.user import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/me", response_model=UserPublic)
def admin_me(current_admin: User = Depends(require_admin)):
    return current_admin


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

    created_slots: list[TimeSlot] = []
    skipped_reasons: list[str] = []
    step = timedelta(minutes=payload.slot_minutes)

    for court in courts:
        current_start = payload.window_starts_at
        # "Hasta" define el último horario de inicio permitido, no el fin del último turno.
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
        created_slots=created_slots,
        skipped_reasons=skipped_reasons,
    )
