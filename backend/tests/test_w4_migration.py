"""W4 Alembic upgrade preserves records created under W2/W3 schema."""
from pathlib import Path
import uuid
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_w4_migration_preserves_existing_snapshot(tmp_path):
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    dbfile = tmp_path / "w3_to_w4.db"
    cfg.attributes["database_url"] = f"sqlite:///{dbfile.as_posix()}"
    command.upgrade(cfg, "20261025_01")
    eng = create_engine(cfg.attributes["database_url"])
    user_id, lot_id, cam_id, snapshot_id = (uuid.uuid4().hex for _ in range(4))
    with eng.begin() as conn:
        conn.execute(text("INSERT INTO users (id,username,password_hash,role) VALUES (:id, 'x','x','admin')"),{"id":user_id})
        conn.execute(text("INSERT INTO parking_lots (id,name) VALUES (:id, 'lot')"),{"id":lot_id})
        conn.execute(text("INSERT INTO cameras (id, parking_lot_id,name) VALUES (:id, :lot, 'cam')"),{"id":cam_id,"lot":lot_id})
        conn.execute(text("INSERT INTO snapshots (id,camera_id,image_path,captured_at,camera_config_version) "
                          "VALUES (:id,:camera,'snapshot.jpg','2026-10-27T00:00:00+00:00',1)"),
                     {"id":snapshot_id,"camera":cam_id})
    eng.dispose()
    command.upgrade(cfg, "head")
    eng = create_engine(cfg.attributes["database_url"])
    with eng.connect() as conn:
        row = conn.execute(text("SELECT id, spots_at_capture, ai_model_version FROM snapshots WHERE id=:id"),{"id":snapshot_id}).one()
        assert row.id == snapshot_id and row.spots_at_capture is None and row.ai_model_version is None
    columns = {col["name"] for col in inspect(eng).get_columns("spot_predictions")}
    assert {"raw_label", "scores", "threshold"} <= columns
    eng.dispose()
