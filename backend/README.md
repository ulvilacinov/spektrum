# German Vocabulary Trainer — Backend

FastAPI backend for an AI-assisted German → Turkish vocabulary learning app.
Current state: **STEP 1** (project skeleton, configuration, database models, initial migration, health endpoint).

## Requirements

- Python 3.12
- Docker (for local PostgreSQL) or an existing PostgreSQL 14+ server

## Setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

## Database

```bash
docker compose up -d postgres        # start PostgreSQL
docker compose ps                    # wait until "healthy"
alembic upgrade head                 # apply migrations
```

Other useful Alembic commands:

```bash
alembic current                      # show applied revision
alembic check                        # fail if models and migrations have drifted
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

## Run

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

## Tests and linting

```bash
pytest
ruff check .
```

## Layout

- `app/api` — HTTP layer only (routes, dependencies). No business logic.
- `app/core` — settings and application errors.
- `app/db` — SQLAlchemy base, session, ORM models.
- `app/domain` — enums and domain types, independent of FastAPI and SQLAlchemy.
- `app/schemas` — Pydantic request/response models.
- `app/repositories`, `app/services` — added as features are implemented.
