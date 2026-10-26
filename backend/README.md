# Backend — AI Smart Parking

**W2 / Task 3.1**: FastAPI, PostgreSQL, SQLAlchemy ORM (8 entities), Alembic,
JWT login and Admin/Operator authorization dependencies. CRUD, snapshot upload,
AI integration, and public user-registration endpoints are **not implemented**.

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
