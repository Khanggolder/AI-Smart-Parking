"""AI Smart Parking backend entry point (W2 infrastructure only)."""

from fastapi import APIRouter, FastAPI

app = FastAPI(
    title="AI Smart Parking API",
    version="0.1.0",
    description="MVP backend; only health endpoint is implemented at W2 infrastructure stage.",
)
api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness endpoint; it does not claim DB or AI availability."""
    return {"status": "ok", "service": "backend"}


app.include_router(api_router)
