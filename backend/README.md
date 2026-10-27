# Backend — AI Smart Parking

**W2 / Task 3.1**: FastAPI, PostgreSQL, SQLAlchemy ORM (8 entities), Alembic,
JWT login, Admin/Operator authorization, and parking lot/camera CRUD.
Snapshots, AI integration, and public user-registration endpoints are **not implemented**.

## Prerequisites and local setup (Windows CMD)

- Python 3.11+, PostgreSQL 18 (or compatible).
- From the repository root, create `.env` from `.env.example` if needed. Set a real
  `DATABASE_URL` for your local PostgreSQL database. Never commit `.env`.
- Generate a signing secret and copy the printed value into `JWT_SECRET_KEY` in `.env`:

```bat
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not use that printed value in git, screenshots, chat, or PR descriptions.
`JWT_SECRET_KEY` must be at least 32 UTF-8 bytes; there is no usable default.
`JWT_EXPIRE_MINUTES=60` creates 1-hour access tokens. Use HTTPS outside local demo.

```bat
cd /d D:\DATT\AI-Smart-Parking\backend
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m pytest -q
```

The existing initial migration already contains the `users` table: no auth migration is necessary.

## Create initial users (local operator action; no public registration)

```bat
.venv\Scripts\python.exe -m app.scripts.create_user --username admin01 --role admin
.venv\Scripts\python.exe -m app.scripts.create_user --username operator01 --role operator
```

Each command prompts twice for a password, without displaying it. Minimum 12
characters; passwords are stored only as Argon2id hashes. Existing usernames
cannot be silently overwritten. Do not pass passwords on the command line.

## Run and verify

```bat
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- `GET /api/v1/health` — public (`{"status":"ok","service":"backend"}`).
- `POST /api/v1/auth/login` — JSON body `{"username":"admin01","password":"..."}`;
  response `access_token`, `token_type: bearer`, `expires_in`.
- `GET /api/v1/auth/me` — header `Authorization: Bearer <access_token>`;
  response `id`, `username`, `role`, `is_active` (no password hash).
- `GET /docs` — Swagger UI; use **Authorize** and paste the access token.

**RBAC:** `require_roles("admin")` protects Admin-only CRUD routes later;
`require_roles("admin", "operator")` permits either role. Roles are read
from PostgreSQL for each request, not trusted from a JWT claim. Missing,
invalid, expired, or inactive accounts return 401; insufficient role returns 403.
Errors implemented by the auth module use `{"error":{"code":...,"message":...,"details":{}}}`.
Schema-level FastAPI 422 responses still use the framework default; this is
not a global error-normalization change.

Security limits of this MVP stage: no login rate limiter, refresh tokens,
logout/revocation list, or password-reset flow. Deploy only behind HTTPS with
additional rate limiting and a strong secret when leaving local demo.

## Testing and Git rules

`python -m pytest -q` covers health, migration, password hashing, JWT expiry,
invalid tokens, disabled users and role checks using disposable SQLite fixtures.
Database integration/migration should also be confirmed against local PostgreSQL.

Reference: `docs/design/backend-architecture-erd.md`,
`docs/api/backend-api-contract-v1.md` and
`docs/requirements/backend-use-cases-test-matrix.md`.
Commit code/tests on a feature branch; link the WBS issue in a PR. Never commit
real `.env` values, tokens, passwords, database files or model weights.

## W2 / Task 3.2: Parking Lots and Cameras

All endpoints use `/api/v1` and require `Authorization: Bearer <access_token>`.
Operator and Admin can read; **only Admin can create or update** resources.

| Method | Path | Role |
| --- | --- | --- |
| GET | `/parking-lots?limit=20&offset=0` | Admin/Operator |
| POST | `/parking-lots` | Admin |
| GET | `/parking-lots/{lot_id}` | Admin/Operator |
| PATCH | `/parking-lots/{lot_id}` | Admin |
| GET | `/cameras?parking_lot_id={uuid}&limit=20&offset=0` | Admin/Operator |
| POST | `/cameras` | Admin |
| GET | `/cameras/{camera_id}` | Admin/Operator |
| PATCH | `/cameras/{camera_id}` | Admin |

Collection responses have `{ "items": [...], "total": 0, "limit": 20, "offset": 0 }`,
with `limit` between 1 and 100. Frontend `src/api/parking.js` accepts this structure.

Create a parking lot: `{ "name": "Lot A", "description": "Gate 1" }`.
Create a camera: `{ "parking_lot_id": "<lot_uuid>", "name": "CAM-01" }`.
PATCH parking lot accepts `name` and/or `description` (including `null` to clear description).
PATCH camera accepts `{ "name": "CAM-02", "expected_camera_config_version": 1 }`.
The expected version is optional for the existing Frontend, but recommended for
concurrent edits. Successful rename increments `config_version`; unchanged name
is a no-op. A stale version returns HTTP 409, code `CAMERA_VERSION_CONFLICT`.

Each successful create/actual update writes an `audit_logs` row in the same DB transaction.
Fields for reference images and parking-lot association are intentionally **not**
editable via the camera PATCH. The image upload endpoint will be implemented later.
No new database migration is required because the W2 schema already contains these fields.

### React CORS (development)

The backend permits `http://localhost:5173` and `http://127.0.0.1:5173` by default.
Override with comma-separated `CORS_ORIGINS` in the root `.env` if your Vite port differs.
Do not set a wildcard origin for a deployed admin application.

### Verify (Windows CMD)

```bat
cd /d D:\DATT\AI-Smart-Parking\backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

In `/docs`, log in as Admin and select **Authorize** to test POST/PATCH.
Log in as Operator to check that GET is allowed while POST/PATCH return 403.
The CRUD tests use disposable SQLite; confirm saves persist in your real PostgreSQL as well.


## W3 phase 1: parking spot polygons (FR-03/FR-04)

Endpoints require JWT. Admin can create, edit and deactivate; Admin and Operator can list.
All coordinates are normalized 0..1 **relative to one camera reference frame**.

| Method | API path | Role | Result |
| --- | --- | --- | --- |
| GET | `/cameras/{camera_id}/spots?include_inactive=false` | Both | `200` with `{items,total,camera_config_version}` |
| POST | `/cameras/{camera_id}/spots` | Admin | `201` |
| PATCH | `/spots/{spot_id}` | Admin | `200` |
| DELETE | `/spots/{spot_id}?expected_camera_config_version=N` | Admin | `204` soft-deactivate |

Create payload:

```json
{
  "spot_code": "P01",
  "polygon": [{"x":0.10,"y":0.20},{"x":0.25,"y":0.20},{"x":0.25,"y":0.40}],
  "expected_camera_config_version": 1
}
```

Patch requires `expected_camera_config_version` and at least one of `spot_code`,
`polygon`. Check the latest camera version in GET response. Every actual edit
increments `camera.config_version` exactly once; a no-op patch does not. A
stale version returns `409 CAMERA_VERSION_CONFLICT`. Deleted spots remain stored
for history (and their spot codes remain reserved); `include_inactive=true`
returns them for administrative inspection.

Polygon validator rejects fewer than 3 or more than 50 points, repeated vertices,
out-of-range coordinates, intersections/touching of nonadjacent edges and
zero/tiny area. Spot code is case-normalized to uppercase and unique per camera.
At most 100 **active** spots per camera are allowed for the AI service.
All writes and audit log entries are committed together.

**Integration boundary:** The React Polygon Editor route currently displays a
placeholder on `main`; this PR exposes Backend APIs only. `PUT /cameras/{id}/reference-image`
(image upload, dimensions and secure storage) is a subsequent W3 task, so saving
polygon geometry here does not yet verify its correspondence to a reference
image. Require a camera reference image before real snapshots/inference. The
snapshot service must copy polygon and configuration version at capture time.
No new Alembic migration is needed.


## W3 phase 2: camera reference images (FR-03/FR-04)

This phase adds two JWT-protected routes:

| Method | Path | Role | Description |
| --- | --- | --- | --- |
| PUT | `/cameras/{camera_id}/reference-image` | Admin | Upload and configure a camera reference frame |
| GET | `/cameras/{camera_id}/reference-image` | Admin/Operator | Retrieve the current image as protected binary content |

The **PUT** request is `multipart/form-data`, not JSON:

- `image`: actual JPEG (`image/jpeg`) or PNG (`image/png`) file, mandatory.
- `expected_camera_config_version`: current positive integer camera version, mandatory.

On success, `200` returns the normal `CameraOut` with updated
`reference_image_path` (an opaque *relative storage key*),
`reference_width`, `reference_height` and incremented `config_version`.
Check `GET /cameras/{id}` before submitting: every camera/polygon edit can
increase the version. Stale versions return `409 CAMERA_VERSION_CONFLICT`.

For a camera **with active parking spots**, replacing/setting the reference
frame returns `409 ACTIVE_SPOTS_EXIST`: first deactivate affected spots and
then upload the frame; redraw fresh polygons afterwards. This prevents silently
reusing normalized polygons over a different frame. **Use a new camera** if you
want to test image upload without disturbing the polygons created during W3.

Upload checks MIME **and decoded content**, detects truncated images, enforces
`UPLOAD_MAX_MB` (10 MiB by default) and a 20-million-pixel maximum. Invalid
image → `422`; unsupported/type mismatch → `415`; oversized file → `413`.
The original client filename is never used. The bytes are stored outside
public static folders with random immutable filenames, under
`REFERENCE_IMAGE_DIR` (`backend/storage/reference-images` by default).
This directory is Git-ignored. No API permits arbitrary filesystem paths.
GET requires Bearer authentication and serves only the image for that camera,
with private/no-store cache headers. Do not serve the storage folder publicly.

A successful upload atomically updates camera metadata/version and its audit log
in one DB transaction; a failed DB transaction removes the new upload. An old
reference image is intentionally **retained** following replacement; automated
retention/garbage collection is not yet implemented. Because the DB schema
already contains all reference-image fields, no new Alembic revision is needed.

Run locally (CMD, inside `backend`):

```bat
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

In Swagger `/docs`, authenticate as `admin01`, find PUT under
`camera-reference-images`, select an actual JPG/PNG file and enter the
current version. Confirm the response metadata, then GET the same camera
image using `operator01`. JPEG/PNG binaries may be displayed/downloaded
by Swagger instead of printed as JSON. PostgreSQL still needs a real local
integration check: the unit tests use disposable SQLite and temp storage.
