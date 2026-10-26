# Backend — AI Smart Parking

**W2 / Task 3.1**: FastAPI, PostgreSQL, SQLAlchemy ORM (8 entities), Alembic,
JWT login, Admin/Operator authorization, and parking lot/camera CRUD.
Parking spots, reference-image upload, snapshots, AI integration, and public user-registration endpoints are **not implemented**.

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
