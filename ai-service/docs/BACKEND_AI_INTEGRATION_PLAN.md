# Backend ↔ AI integration plan (W8)

Status: proposal for Nam's review. Source contracts: `docs/api/backend-api-contract-v1.md` at `origin/main` (`8b307a2`) and `ai-service/docs/AI_API_CONTRACT.md`; runtime is `ai-service/src/service.py`. This document does not change either contract or backend code.

## Contract comparison

| Concern | Backend design v1 | AI runtime | Adapter action |
|---|---|---|---|
| Public snapshot | `POST /api/v1/snapshots`, JWT, multipart `camera_id`, `captured_at`, `image`; async `202` job | No public snapshot endpoint or persistence | Backend owns auth, job, snapshot timestamp and database. |
| Internal inference | `POST {AI_SERVICE_URL}/predict`, image + JSON metadata | `POST {AI_SERVICE_URL}/v1/infer`, multipart `image`, `camera_id`, `spots_json` | Set URL to base origin and call `/v1/infer`; agree on contract correction with Nam. |
| Polygon | list of `{x,y}` normalized objects | 3–50 `[x,y]` normalized pairs per spot, 1–100 spots | Validate camera config version; map each object to pair, preserve vertex order and normalized frame. |
| Spot identity | UUID `spot_id`, display `spot_code` | `spot_id` is opaque 1–128 character string | Send persistent UUID as string; keep spot code for UI. Verify exact IDs/order and no duplicates on return. |
| Camera identity | UUID and camera config version | `camera_id` echoed, no config version | Backend binds snapshot to stored camera/version and verifies echoed ID. Do not expect AI to validate camera ownership. |
| Prediction | `label`, `confidence`, `model_version`, `inference_ms` example | `raw_label`, final `label`, `confidence`, `scores`, global `model_version`, `threshold`, `processing_time_ms` | Persist final `label` separately from `raw_label`, scores, threshold, model version and capture time. Map processing time to internal metric only; it includes upload/validation/crop/inference, not network. |
| Errors | Backend async job `failed`; 422 schema and 503 AI offline | Structured `error.code/message` for handler errors; 413/415/422/503/500; pre-handler multipart may differ | Mark job failed, preserve previous completed snapshot, never create fake predictions. |

`empty = 0`, `occupied = 1`; AI final `unknown` means confidence below 0.90, while `raw_label` and scores remain available for audit. UNKNOWN is not an AI transport error and must remain a separate final label in DB, summary and UI. FULL and STALE are backend business logic; any UNKNOWN prevents a certain FULL alert under the current backend contract.

## Request/response mapping

1. Backend accepts one authenticated snapshot, stores `captured_at`, image reference, `camera_id`, `camera_config_version` and immutable ordered active spot UUID list for the job. Do not send ground truth or review labels.
2. Before call, confirm image and spot polygons came from the same camera configuration. Convert `{x: 0.12, y: 0.30}` to `[0.12, 0.30]`. Send `spots_json = [{"spot_id":"<uuid>","polygon":[[x,y],...]}]`. AI limits: JPEG/PNG, 10 MiB, 20 megapixels, 1–100 spots, 256 KiB JSON.
3. POST multipart `image`, `camera_id`, `spots_json` to `/v1/infer`. A `200` response must contain matching `camera_id`, exactly one prediction per requested spot in the requested order, finite scores/confidence in `[0,1]`, a nonempty `model_version` and threshold 0.90 for this release. Check `label ∈ {empty,occupied,unknown}`. Reject partial or malformed responses atomically.
4. Persist `snapshot_id`, `captured_at`, camera config/polygon version, stable spot UUID, `raw_label`, final `label`, `confidence`, scores, `model_version`, threshold and received time. Backend review labels are append-only and must not overwrite AI output. `spot_code` is joined from backend configuration for display.
5. Convert final labels into backend `predicted_label` and `effective_label` (until review). Backend computes summary from final labels; include UNKNOWN count. `processing_time_ms` is AI handler timing; it is not equivalent to round-trip latency or the design's `inference_ms`.

Illustrative backend-side Python client (not a committed runtime adapter):

```python
import json
import httpx

def call_ai(base_url, camera_id, spots, image_bytes):
    payload = [
        {"spot_id": str(s["id"]),
         "polygon": [[p["x"], p["y"]] for p in s["polygon"]]}
        for s in spots
    ]
    with httpx.Client(timeout=httpx.Timeout(10.0, connect=2.0)) as client:
        response = client.post(
            base_url.rstrip("/") + "/v1/infer",
            data={"camera_id": str(camera_id), "spots_json": json.dumps(payload)},
            files={"image": ("snapshot.jpg", image_bytes, "image/jpeg")},
        )
    response.raise_for_status()
    result = response.json()
    expected = [item["spot_id"] for item in payload]
    actual = [item["spot_id"] for item in result["predictions"]]
    if result["camera_id"] != str(camera_id) or actual != expected:
        raise ValueError("AI response does not match snapshot spot mapping")
    return result  # Validate all fields before one atomic database write.
```

Timeout above is a demo starting value, **not measured production SLO**. Nam should benchmark target hardware and set connect/read/total limits accordingly. Retry transport timeout/503 only with bounded backoff while the *same* snapshot job remains idempotent; never create duplicate prediction rows. Do not retry 413/415/422 unchanged. On 500 or malformed 200, log correlation/snapshot ID and safe error code; fail job without partial write. `/health` checks process liveness; `/ready` must be 200 before treating AI as usable. Restrict service to private network: AI has no auth and trusts backend-provided camera/spot IDs.

## Integration tests and decisions for Nam

- Real rc2 checkpoint: 37 distinct polygons → 37 predictions and exact ID order; verify `model_version` and threshold. Include one validation/development UNKNOWN case, invalid polygon/422, unavailable model/503, timeout, malformed/partial response and duplicate spot ID rejection.
- Snapshot → queued/completed or failed job → stored predictions → history/summary → frontend, including camera config changed during job, retry idempotency, stale data and review override. Do not call mock output real inference.
- Agree whether backend contract replaces `/predict` with `/v1/infer` and records multipart field/schema mapping; how polygon/camera config version is frozen; whether DB stores `raw_label`, scores, threshold and timing; retry/SLO/security and package distribution. Update backend contract in Nam's implementation PR after agreement.

Release ZIP is ignored by Git. Khang must deliver `ai-smart-parking-model-v0.1.0-rc2.zip` through an agreed internal channel; Nam should verify ZIP SHA-256 `6073421790203b850f71e6b013ad49a2ae3b42417ec00ec08236483a1603b27a`, extract and run `verify_release.py` before starting Uvicorn. Cloning GitHub alone does not provide model weights. See `RELEASE_README.md` and `BACKEND_HANDOVER.md` for install/environment steps. Frontend receives final labels from backend: green empty, red occupied, gray unknown; unavailable/stale is separate.
