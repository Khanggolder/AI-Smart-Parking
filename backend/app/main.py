"""AI Smart Parking backend REST API (W2 JWT authentication foundation)."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.parking_lots import router as parking_lots_router
from app.api.cameras import router as cameras_router
from app.api.spots import router as spots_router
from app.api.reference_images import router as reference_images_router
from app.api.snapshots import router as snapshots_router
from app.core.config import get_settings
from app.core.errors import APIError, api_error_handler

app = FastAPI(
    title="AI Smart Parking API",
    version="0.6.0",
    description="W2/W3 management APIs and W4 snapshot inference jobs.",
)
app.add_exception_handler(APIError, api_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness only, not a DB or AI readiness guarantee."""
    return {"status": "ok", "service": "backend"}


app.include_router(api_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(parking_lots_router, prefix="/api/v1")
app.include_router(cameras_router, prefix="/api/v1")
app.include_router(spots_router, prefix="/api/v1")

app.include_router(reference_images_router, prefix="/api/v1")

app.include_router(snapshots_router, prefix="/api/v1")
