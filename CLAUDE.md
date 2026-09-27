# German Vocabulary Trainer — Project Guide

AI-assisted German → Turkish vocabulary learning app. A user uploads a PDF of vocabulary,
the backend extracts chapters ("Kapitel N") and vocabulary items once, stores them in
PostgreSQL, and all learning (batches, quizzes, weak/mastered tracking) runs from the DB.

The full product specification lives in `docs/SPEC.md`. Read it before starting a new step.

## Working rules

- Build incrementally, one STEP at a time. Stop after each step and wait for the user.
- Do not implement the frontend until the first backend milestone works.
- Do not replace existing architecture without a clear technical reason; explain it first.
- Every step must leave the app runnable: `pytest` and `ruff check .` pass, migrations apply.
- Keep the MVP simple; prefer clean, production-friendly code over shortcuts.
- When a decision is needed, pick a sensible default and state it briefly.
- Learner-facing AI feedback is in Turkish.

## Stack

Python 3.12, FastAPI, Uvicorn, Pydantic v2, pydantic-settings, SQLAlchemy 2.x (sync, psycopg 3),
Alembic, PostgreSQL 16, PyMuPDF, Gemini (behind a provider abstraction), pytest, ruff.

## Architecture (backend/)

- `app/api/` — HTTP only: routes, dependencies. **No business logic in route handlers.**
- `app/core/` — `config.py` (Settings via `get_settings()`), `exceptions.py` (`AppError`,
  `NotFoundError`, `ConflictError` → JSON `{"error": {code, message, details}}`).
- `app/db/` — `Base` with naming convention, `enum_column()` helper, `session.py`, `models/`.
- `app/domain/` — enums and domain types, independent of FastAPI/SQLAlchemy.
- `app/schemas/` — Pydantic request/response models.
- `app/repositories/` — DB access (to be added).
- `app/services/{pdf,ai,documents,learning}/` — business logic (to be added).

## Conventions

- Enums are `StrEnum` in `app/domain/enums.py`, stored as VARCHAR via `enum_column()`,
  not native PostgreSQL ENUMs.
- Integer primary keys. `user_id` is a nullable int without FK until users exist.
- Every new model is imported in `app/db/models/__init__.py`.
- Schema changes go through Alembic: `alembic revision --autogenerate -m "..."`, then review
  the generated file by hand. `alembic check` must report no drift.
- Services own transactions (commit); routes never commit.
- The AI layer is an `AIProvider` interface; Gemini is one implementation. Business logic
  must never import Gemini directly.
- AI output for document parsing is always structured JSON validated by Pydantic.
  Vocabulary items must originate from the PDF; the AI may add examples/translations only.
- Answer checking: exact match → normalized deterministic comparison → AI only when needed.
- Progression logic (new/learning/weak/mastered) lives in one isolated service.
- Tests use in-memory SQLite (`tests/conftest.py`) for speed; migrations are verified
  against real PostgreSQL.

## Commands (run from backend/)

```bash
docker compose up -d postgres
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000/docs
pytest
ruff check .
```

## Status

- [x] STEP 1 — skeleton, config, Document/Chapter/VocabularyItem models, migration 0001,
      `GET /api/health`.
- [ ] STEP 2 — `POST /api/documents` (PDF upload, validation, storage in `uploads/`),
      `GET /api/documents`, `GET /api/documents/{id}`, PyMuPDF page-by-page extraction
      service with page numbers preserved. No AI yet.
- [ ] STEP 3 — `AIProvider` + `GeminiAIProvider`, chapter detection, vocabulary extraction,
      `POST /api/documents/{id}/analyze`.
- [ ] STEP 4 — `GET /api/documents/{id}/chapters` (with `vocabulary_count`),
      `GET /api/chapters/{id}/vocabulary`. First milestone complete.
- [ ] Later — learning sessions, quizzes, answer evaluation, progress, weak review, frontend.
