"""W2 DB validation with disposable SQLite; PostgreSQL remains production target."""

import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Camera, ParkingLot, ParkingSpot, User

EXPECTED_TABLES = {
    "users", "parking_lots", "cameras", "parking_spots", "snapshots",
    "spot_predictions", "spot_reviews", "audit_logs",
}


def test_orm_has_eight_entities():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_user_role_check():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(username="reader", password_hash="hashed", role="invalid"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    engine.dispose()


def test_spot_code_unique_per_camera():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        lot = ParkingLot(name="Test lot")
        # Explicit IDs let us reference parent records before they are flushed.
        lot.id = uuid.uuid4()
        camera = Camera(id=uuid.uuid4(), parking_lot_id=lot.id, name="CAM-01")
        db.add_all([lot, camera])
        db.commit()
        polygon = [{"x": 0.1, "y": 0.2}, {"x": 0.2, "y": 0.2}, {"x": 0.2, "y": 0.3}]
        db.add(ParkingSpot(camera_id=camera.id, spot_code="P01", polygon=polygon))
        db.commit()
        db.add(ParkingSpot(camera_id=camera.id, spot_code="P01", polygon=polygon))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    engine.dispose()


def test_alembic_initial_upgrade_and_downgrade(tmp_path):
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    sqlite_db = tmp_path / "schema.db"
    cfg.attributes["database_url"] = f"sqlite:///{sqlite_db.as_posix()}"
    command.upgrade(cfg, "head")
    engine = create_engine(cfg.attributes["database_url"])
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    engine.dispose()
    command.downgrade(cfg, "base")
    engine = create_engine(cfg.attributes["database_url"])
    assert not (EXPECTED_TABLES & set(inspect(engine).get_table_names()))
    engine.dispose()
