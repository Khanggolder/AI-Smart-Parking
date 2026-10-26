"""AI Smart Parking backend REST API (W2 JWT authentication foundation)."""

from fastapi import APIRouter, FastAPI

from app.api.auth import router as auth_router
from app.core.errors import APIError, api_error_handler

app = FastAPI(
    title="AI Smart Parking API",
    version="0.2.0",
    description="W2 foundation: health, JWT login, current user, role dependencies.",
)
app.add_exception_handler(APIError, api_error_handler)
api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness only, not a DB or AI readiness guarantee."""
    return {"status": "ok", "service": "backend"}


app.include_router(api_router)
app.include_router(auth_router, prefix="/api/v1")
