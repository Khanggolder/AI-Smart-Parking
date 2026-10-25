"""FastAPI boundary for one camera snapshot and configured spot polygons."""
from __future__ import annotations

from contextlib import asynccontextmanager
import json
import logging
from time import perf_counter

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import torch

from .inference import InferenceEngine
from .model_loader import ModelLoader, Settings
from .preprocessing import InputError

logger = logging.getLogger(__name__)


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(settings: Settings | None = None, loader_factory=ModelLoader) -> FastAPI:
    settings = settings or Settings.load()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.engine = InferenceEngine(loader_factory(settings))
            app.state.load_error = None
            logger.info("AI model ready on %s", app.state.engine.loader.device)
        except Exception as exc:
            app.state.engine = None
            app.state.load_error = str(exc)
            logger.error("AI model unavailable: %s", exc)
        yield

    app = FastAPI(title="AI Smart Parking inference", version="1.0", lifespan=lifespan)
    app.state.engine = None
    app.state.load_error = "Model initialization pending"

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return error(422, "INVALID_REQUEST", "Required multipart fields are missing or invalid")

    @app.get("/health")
    def health():
        return {"status": "alive"}

    @app.get("/ready")
    def ready():
        engine = app.state.engine
        if engine is None:
            return error(503, "MODEL_UNAVAILABLE", app.state.load_error or "Model is not loaded")
        return {"status": "ready", "device": str(engine.loader.device),
                "model_version": engine.loader.model_version,
                "threshold": engine.loader.threshold}

    @app.post("/v1/infer")
    def infer(image: UploadFile = File(...), camera_id: str = Form(...), spots_json: str = Form(...)):
        start = perf_counter()
        engine = app.state.engine
        if engine is None:
            return error(503, "MODEL_UNAVAILABLE", app.state.load_error or "Model is not loaded")
        if not camera_id.strip() or len(camera_id) > 128:
            return error(422, "INVALID_CAMERA_ID", "camera_id must be 1 to 128 nonblank characters")
        if image.content_type not in ("image/jpeg", "image/png"):
            return error(415, "UNSUPPORTED_MEDIA_TYPE", "image must be JPEG or PNG")
        data = image.file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            return error(413, "IMAGE_TOO_LARGE", "Image exceeds configured byte limit")
        if len(spots_json.encode("utf-8")) > 262144:
            return error(413, "SPOTS_JSON_TOO_LARGE", "spots_json exceeds 256 KiB")
        try:
            spots = json.loads(spots_json)
        except (ValueError, TypeError):
            return error(422, "INVALID_SPOTS_JSON", "spots_json must be a JSON array")
        try:
            result = engine.infer(data, spots)
        except InputError as exc:
            return error(422, exc.code, str(exc))
        except torch.cuda.OutOfMemoryError:
            logger.exception("CUDA out of memory during inference")
            return error(503, "INFERENCE_RESOURCE_ERROR", "GPU memory exhausted")
        except Exception:
            logger.exception("Inference failed")
            return error(500, "INFERENCE_ERROR", "Inference failed")
        return {"camera_id": camera_id, "model_version": engine.loader.model_version,
                "threshold": engine.loader.threshold, "predictions": result.predictions,
                "processing_time_ms": round((perf_counter() - start) * 1000, 3)}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.service:app", host="127.0.0.1", port=Settings.load().port)
