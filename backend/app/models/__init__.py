"""Import all model classes to register them in Base.metadata."""

from app.models.entities import (
    AuditLog,
    Camera,
    ParkingLot,
    ParkingSpot,
    Snapshot,
    SpotPrediction,
    SpotReview,
    User,
)

__all__ = ["User", "ParkingLot", "Camera", "ParkingSpot", "Snapshot", "SpotPrediction", "SpotReview", "AuditLog"]
