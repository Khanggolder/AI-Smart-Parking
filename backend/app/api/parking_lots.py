"""FR-02: parking-lot CRUD (read for both roles, writes for admins)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.errors import APIError
from app.db.session import get_db
from app.models import AuditLog, ParkingLot, User
from app.schemas.parking import ParkingLotCreate, ParkingLotOut, ParkingLotPage, ParkingLotPatch

router = APIRouter(prefix="/parking-lots", tags=["parking-lots"])
reader = require_roles("admin", "operator")
writer = require_roles("admin")


def find_lot(db: Session, lot_id: UUID) -> ParkingLot:
    lot = db.get(ParkingLot, lot_id)
    if lot is None:
        raise APIError(404, "PARKING_LOT_NOT_FOUND", "Parking lot not found")
    return lot


@router.get("", response_model=ParkingLotPage)
def list_parking_lots(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _user: User = Depends(reader),
    db: Session = Depends(get_db),
):
    total = db.scalar(select(func.count()).select_from(ParkingLot)) or 0
    lots = db.scalars(select(ParkingLot).order_by(ParkingLot.created_at, ParkingLot.id).limit(limit).offset(offset)).all()
    return ParkingLotPage(items=lots, total=total, limit=limit, offset=offset)


@router.post("", status_code=201, response_model=ParkingLotOut)
def create_parking_lot(payload: ParkingLotCreate, user: User = Depends(writer), db: Session = Depends(get_db)):
    lot = ParkingLot(**payload.model_dump())
    db.add(lot)
    db.flush()
    db.add(AuditLog(actor_id=user.id, action="parking_lot.created", entity_type="parking_lot", entity_id=lot.id))
    db.commit()
    db.refresh(lot)
    return lot


@router.get("/{lot_id}", response_model=ParkingLotOut)
def get_parking_lot(lot_id: UUID, _user: User = Depends(reader), db: Session = Depends(get_db)):
    return find_lot(db, lot_id)


@router.patch("/{lot_id}", response_model=ParkingLotOut)
def patch_parking_lot(
    lot_id: UUID, payload: ParkingLotPatch, user: User = Depends(writer), db: Session = Depends(get_db)
):
    lot = find_lot(db, lot_id)
    updates = payload.model_dump(exclude_unset=True)
    changed = False
    for key, value in updates.items():
        if getattr(lot, key) != value:
            setattr(lot, key, value)
            changed = True
    if changed:
        db.add(AuditLog(actor_id=user.id, action="parking_lot.updated", entity_type="parking_lot", entity_id=lot.id))
        db.commit()
        db.refresh(lot)
    return lot
