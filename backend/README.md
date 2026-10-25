# Backend — AI Smart Parking

**W2 / Task 3.1.1–3.1.2**: FastAPI framework, SQLAlchemy ORM (8 entities), Alembic initial migration.
Authentication, CRUD, upload snapshot and AI integration are **not implemented** yet.

## Environment

- Python 3.11+ (tested with Python 3.13)
- PostgreSQL for real development, configured by `DATABASE_URL` in repository root `.env` (not committed)
- From repository root on Windows CMD:

```bat
cd /d D:\DATT\AI-Smart-Parking\backend
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Copy the root `.env.example` to `.env` and set a real local `DATABASE_URL` matching your PostgreSQL credentials (the `change_me` value is a placeholder). Don't commit `.env`.

## Start backend and check health

```bat
uvicorn app.main:app --reload --port 8000
```

- `http://127.0.0.1:8000/api/v1/health` → `{"status":"ok","service":"backend"}`
- `http://127.0.0.1:8000/docs` → Swagger UI (only health is implemented)
- Health endpoint is a **liveness check**, not PostgreSQL/AI readiness.

## Migration

Once PostgreSQL is running and the database/user have been created:

```bat
alembic upgrade head
alembic current
```

`alembic upgrade head` creates 8 tables. Do not run `Base.metadata.create_all()` on a persistent database; schema changes must be reviewed through Alembic migrations.

## Tests without PostgreSQL

```bat
python -m pytest -q
```

Tests use disposable SQLite only to exercise DB constraints/migration structure. PostgreSQL must also be exercised in integration testing before declaring W2 finished.

## Contract and branch policy

- Canonical design: `docs/design/backend-architecture-erd.md`
- API contract: `docs/api/backend-api-contract-v1.md`
- Use cases/tests: `docs/requirements/backend-use-cases-test-matrix.md`
- Use a feature branch, small Conventional Commits, Pull Request to `main`. Do not commit passwords or `.env`.
