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
  `NotFoundError`, `ConflictError`, `UnprocessableError`, `PayloadTooLargeError`,
  `UnsupportedMediaTypeError` → JSON `{"error": {code, message, details}}`; `code` can be
  overridden per raise).
- `app/db/` — `Base` with naming convention, `enum_column()` helper, `session.py`, `models/`.
- `app/domain/` — enums and domain types, independent of FastAPI/SQLAlchemy.
- `app/schemas/` — Pydantic request/response models.
- `app/repositories/` — DB access only; never commits (`DocumentRepository`).
- `app/services/pdf/` — `PdfTextExtractor`: PyMuPDF page-by-page text, 1-based page numbers,
  blank pages kept. No DB/HTTP knowledge.
- `app/services/documents/` — `DocumentService` (upload validation, storage, CRUD,
  `extract_pages(document_id)` for STEP 3) and `LocalFileStorage` (keys relative to `uploads/`).
- `app/services/ai/` — `AIProvider` (ABC), `GeminiAIProvider`, `create_ai_provider()` (the only
  place that names concrete providers), provider-independent `prompts.py`, and the structured
  output contract in `schemas.py` (lenient Pydantic models).
- `app/services/documents/analysis.py` — `DocumentAnalysisService`: status claim (atomic
  UPDATE), page extraction, AI chapter detection → `chapter_planning.plan_chapters()`,
  concurrent per-chapter/per-chunk vocabulary extraction → `vocabulary_grounding.ground_items()`
  (rejects items whose `source_text` is not on the page), one final transaction.
- `app/services/documents/chapters.py` — `ChapterService`: read access to chapters and
  vocabulary (routes build responses with `ChapterSummaryRead.from_chapter`).
- `app/services/learning/` — `progression.py`: `ProgressionPolicy` / `SimpleProgressionPolicy`,
  the only code that changes a `UserVocabularyProgress` status (wired in
  `get_progression_policy()`); `sessions.py`: `LearningSessionService`;
  `question_generation.py`: deterministic, weighted question builders (no AI);
  `quiz.py`: `QuizService`; `answer_matching.py`: deterministic exact/normalized matching
  with "/" alternatives and optional "( )" parts; `answers.py`: `AnswerService`;
  `progress.py`: `ProgressService` (read-only progress and weak-word views).
- Services that need the AI only sometimes get `get_ai_provider_factory()` (lazy), so
  deterministic paths work without an AI configuration.
- The acting user comes from `get_current_user_id()` (`DEFAULT_USER_ID` until auth exists).
- Services are wired in `app/api/dependencies.py` (e.g. `DocumentServiceDep`).

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
  This is enforced deterministically by `vocabulary_grounding`, not only by the prompt.
- Tests never call a real AI: `tests/fake_ai.py` overrides `get_ai_provider`.
- Answer checking: exact match → normalized deterministic comparison → AI only when needed.
- Progression logic (new/learning/weak/mastered) lives in one isolated service.
- Tests use in-memory SQLite (`tests/conftest.py`) for speed; migrations are verified
  against real PostgreSQL.

## Frontend (frontend/)

React 19 + TypeScript 5.9 (Vite), React Router, TanStack Query, `openapi-fetch` with types
generated from the backend's OpenAPI (`npm run gen:api` → `src/api/schema.d.ts`, committed;
regenerate after every API change). UI texts are Turkish; backend error codes are mapped to
Turkish messages in `src/api/client.ts`. Vite proxies `/api` to `127.0.0.1:8000` (no CORS).
Every step must leave `npm test`, `npm run lint` and `npm run build` passing.

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
- [x] STEP 2 — `POST /api/documents` (PDF upload: extension/content-type → 415, size limit
      → 413, empty/non-PDF/corrupt/encrypted → 422; saved as `uploads/<uuid>.pdf`, file removed
      if the DB commit fails), `GET /api/documents` (newest first, `limit`/`offset`),
      `GET /api/documents/{id}`, `PdfTextExtractor` + `DocumentService.extract_pages()`.
      No schema change. Page text is not persisted; STEP 3 extracts it on analyze.
- [x] STEP 3 — `AIProvider` + `GeminiAIProvider` (google-genai, `response_schema`, SDK retries
      on 429/5xx, one retry on invalid JSON, 502 on AI errors, 503 without `GEMINI_API_KEY`),
      AI chapter detection (headings or running headers, `starts_mid_page`), vocabulary
      extraction in chunks of `AI_MAX_PAGES_PER_REQUEST` pages with `AI_MAX_CONCURRENCY`
      parallel requests, grounding against page text, per-chapter de-duplication,
      `POST /api/documents/{id}/analyze[?force=true]` (synchronous; 409 if parsed/in progress).
      No schema change. Default model `gemini-3.8-flash` (2.5-flash is closed to new users).
      Free tier = 5 requests/min/model → `AI_REQUESTS_PER_MINUTE` (process-wide limiter per
      model); 429 waits the server's `retry in Ns` (max 90 s, 3×), longer = quota exhausted.
      Verified end-to-end on 2026-09-28 (paid tier) with the real 24-page Spektrum B1+ PDF:
      12 chapters with correct page ranges, 738 items, 0 rejected, ~150 s at 60 RPM; every
      bulleted German entry covered. Grounding ignores whitespace so entries wrapped across
      lines (soft hyphens, "Dürer-
Haus", "sinkt/
geht") are not rejected.
- [x] STEP 4 — `GET /api/documents/{id}/chapters` (reading order, `vocabulary_count` via one
      LEFT JOIN/GROUP BY query, `[]` before analysis, 404 unknown document) and
      `GET /api/chapters/{id}/vocabulary` (all item fields in PDF order, 404 unknown chapter),
      served by `ChapterService`. **First milestone complete** (verified with the real PDF:
      12 chapters, 738 items).
- [x] STEP 5 — `UserVocabularyProgress`, `LearningSession`, `LearningSessionItem` (migration
      0002), `SimpleProgressionPolicy` (new→learning on study, wrong→weak, 2 correct in a
      row→mastered), `POST /api/learning-sessions` {chapter_id, batch_size 1-100, default 10} picks the
      chapter's next unstudied items in PDF order (409 `no_new_vocabulary` when done),
      `GET /api/learning-sessions/{id}/items` (with status; other users' sessions → 404).
      Re-analysis with force=true cascades and deletes sessions and progress.
- [x] STEP 6 — `QuizQuestion` (migration 0003), `POST /api/learning-sessions/{id}/quiz`: one
      question per session word, built from stored fields without AI (german_to_turkish,
      turkish_to_german, article, preposition, verb_conjugation, sentence_translation;
      weighted 2/3/2/2/1/1, seeded by session id). Turkish question texts; expected answers
      are never returned. 201 on create, 200 with the same quiz afterwards. fill_blank and
      free_sentence need AI and are not generated yet.
- [x] STEP 7 — `POST /api/quiz/{question_id}/answer` {answer}: exact → normalized (case,
      punctuation, "/" alternatives, optional "( )" parts, Turkish letters without
      diacritics, German ae/oe/ue/ss) → rule for closed types (article, preposition,
      verb_conjugation) or `AIProvider.evaluate_answer` for open types. Turkish feedback in
      `ai_feedback`; score, corrected_answer, error_type, evaluation_method, answered_at stored
      (migration 0004). One answer per question (atomic conditional UPDATE, 409 otherwise);
      AI failure stores nothing. Updates progress via `ProgressionPolicy.record_answer`,
      session counters and `completed_at`. Verified with real Gemini (~2–5 s per AI answer).
- [x] STEP 8 — `LearningSession.mode` new|review (migration 0005): review sessions pick
      studied, unmastered words (weak first, longest due first). New batches are locked
      (409 `batch_locked`) until every studied word of the chapter is mastered
      (`ProgressionPolicy.is_new_batch_unlocked`). `GET /api/progress?document_id=` (per-chapter
      new/learning/weak/mastered, mastery_ratio, can_start_new_batch, can_review) and
      `GET /api/review/weak` (with the latest mistake and its Turkish feedback). The full
      spec cycle is covered by one API test and was verified on PostgreSQL with real Gemini.
- [x] F1 — frontend scaffold, typed API client, documents page: list with status, PDF
      upload (client-side .pdf check, Turkish API errors), analyze / re-analyze (confirmation,
      because re-analysis deletes learning progress), polling while a document is parsing.
- [ ] F2 — chapter list with progress (`/api/progress`), start new batch / review.
- [ ] F3 — learning screen (session words) and quiz with Turkish feedback per answer.
- [ ] F4 — weak words with last mistakes, batch-locked / unlocked flow.
