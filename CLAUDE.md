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
Alembic, PostgreSQL 16, PyMuPDF, Gemini / OpenAI / Anthropic (behind a provider abstraction,
chosen per user), cryptography (Fernet), pytest, ruff.

## Architecture (backend/)

- `app/api/` — HTTP only: routes, dependencies. **No business logic in route handlers.**
  `frontend.py`: `mount_frontend()` serves the built SPA (`FRONTEND_DIST_DIR`) with an
  `index.html` fallback; unknown `/api/*` paths stay JSON 404s.
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
- `app/services/ai/` — `AIProvider` (ABC), `StructuredAIProvider` (`base.py`: shared validation
  and one retry), `GeminiAIProvider` (response_schema, rate limiter), `OpenAIProvider`
  (json_schema; `json_schema=False` = JSON mode + schema in the prompt for OpenAI-compatible
  services), `AnthropicProvider` (forced tool call), `create_ai_provider(AIConfig, settings)`
  (the only place that names concrete providers), `errors.provider_error()` (vendor errors →
  `ai_invalid_key` / `ai_model_not_found` / `ai_quota_exhausted` / `ai_provider_error`),
  provider-independent `prompts.py`, and the structured output contract in `schemas.py`.
- `app/services/ai_settings/` — `AISettingsService`: each user's provider, model, base URL
  (https only) and API key, encrypted with `app/core/crypto.SecretBox` (Fernet from
  `SECRET_KEY`; production refuses to start without it). `provider_for(user_id)` is the only
  way business logic gets an AI; without settings it raises `ai_not_configured`.
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
- `app/services/chat/` — `ChatService`: stateless tutor chat (client sends the history, the
  last `MAX_HISTORY_MESSAGES` go to `AIProvider.chat()`; the prompt is `prompts.CHAT_SYSTEM`).
- Services that need the AI only sometimes get `get_ai_provider_factory()` (lazy), so
  deterministic paths work without an AI configuration.
- The acting user comes from `get_current_user_id()` → `get_current_user()` (HttpOnly session
  cookie → `AuthService.authenticate`). Every router except health/auth requires it
  (`app/api/router.py`). Documents are private: repositories filter by `user_id`, and a
  foreign document/chapter is a 404. Accounts: `python -m app.cli` (no public sign-up).
- `app/services/auth/` — `AuthService` (scrypt passwords in `app/core/security.py`, sessions
  stored as SHA-256 token hashes, 30 days sliding), `LoginThrottle` (in-memory, per username
  and client).
- Services are wired in `app/api/dependencies.py` (e.g. `DocumentServiceDep`).

## Conventions

- Enums are `StrEnum` in `app/domain/enums.py`, stored as VARCHAR via `enum_column()`,
  not native PostgreSQL ENUMs.
- Integer primary keys. `user_id` columns are FKs to `users.id` (ON DELETE CASCADE).
- Every new model is imported in `app/db/models/__init__.py`.
- Schema changes go through Alembic: `alembic revision --autogenerate -m "..."`, then review
  the generated file by hand. `alembic check` must report no drift.
- Services own transactions (commit); routes never commit.
- The AI layer is an `AIProvider` interface with Gemini, OpenAI(-compatible) and Anthropic
  implementations; each user picks one on `/settings`. Business logic must never import a
  vendor SDK. There is no server-wide AI key.
- AI output for document parsing is always structured JSON validated by Pydantic.
  Vocabulary items must originate from the PDF; the AI may add examples/translations only.
  This is enforced deterministically by `vocabulary_grounding`, not only by the prompt.
- Tests never call a real AI: `tests/fake_ai.py` overrides `get_ai_provider`. The `client`
  fixture is logged in as `TEST_USER_ID` (override of `get_current_user_id`);
  `tests/test_auth_api.py` uses the real cookie flow. Frontend tests are logged in by default
  (`mockApi` answers `/api/auth/me` with `TEST_USER`).
- Answer checking: exact match → normalized deterministic comparison → AI only when needed.
- Progression logic (new/learning/weak/mastered) lives in one isolated service.
- Tests use in-memory SQLite (`tests/conftest.py`) for speed; migrations are verified
  against real PostgreSQL.

## Frontend (frontend/)

React 19 + TypeScript 5.9 (Vite), React Router, TanStack Query, `openapi-fetch` with types
generated from the backend's OpenAPI (`npm run gen:api` → `src/api/schema.d.ts`, committed;
regenerate after every API change). UI texts are Turkish; backend error codes are mapped to
Turkish messages in `src/api/client.ts`. Vite proxies `/api` to `127.0.0.1:8000` (no CORS).
Every step must leave `npm test`, `npm run lint`, `npm run format:check` and `npm run build`
passing.

## Commands (run from backend/)

```bash
docker compose up -d postgres
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000/docs
pytest
ruff check .
```

Self-hosting on this PC: `.\start.ps1` in the repo root (Docker → Postgres → migrations →
frontend build → uvicorn on 0.0.0.0:8000 serving UI + API). See the root `README.md`.
`DATABASE_URL` uses `127.0.0.1`, not `localhost`: Postgres is published on 127.0.0.1 only and
on Windows a `::1` attempt stalls for minutes before falling back.

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
- [x] F2 — `/documents/:id`: chapters with segmented progress (`/api/progress`), batch size
      5/10/20, "new batch" / "review" buttons enabled by `can_start_new_batch` / `can_review`;
      `/sessions/:id`: learning screen with word cards (meaning, grammar, example, PDF page).
      Backend: `GET /api/learning-sessions/{id}` (with `chapter_title`, `document_id`).
- [x] F3 — `/sessions/:id/quiz`: one question at a time (resumes at the first unanswered),
      German/Turkish input without spellcheck/autocorrect, feedback card after each answer
      (correct/wrong, book answer, AI correction, Turkish explanation, error type, score, new
      word status), retry after an AI failure, summary with "review weak words". Prettier added
      (`npm run format`, `format:check`).
- [x] F4 — `/documents/:id/weak`: weak words grouped by chapter in reading order, each with
      its latest mistake (question, answer, book answer, correction, Turkish explanation, error
      type) and wrong/correct counts; "review this chapter" starts a review session with
      batch_size = the chapter's weak count (review picks weak words first). Linked from the
      document page (when weak > 0) and the quiz summary. Answering invalidates the weak list.
- [x] F5 — playful design: Nunito/Fredoka (Google Fonts), cream/violet palette with dark mode,
      chunky 3D buttons, pretzel header, emoji status badges (CSS `content: '…' / ''`, so no
      screen-reader noise), coloured chapter numbers, der/die/das colour coding on word cards
      (`lib/fun.ts` `articleOf`), quiz streak counter, stable per-question cheers, confetti on
      correct answers, shake on wrong ones, medal + score ring in the summary. All motion is
      off under `prefers-reduced-motion`. No API change.
- [x] F6 — "📖 Dilbilgisi" header button → native `<dialog>` with static grammar reference
      (`lib/grammar.ts`, markup "[…]" highlights endings): cases with Turkish equivalents and
      dative verbs, der/ein/kein tables, the three adjective ending tables ("ein neues Haus"),
      personal pronouns, prepositions by case with contractions. Remembers the last topic while
      the app is open. Tests stub `showModal`/`close` in `src/test/setup.ts` (jsdom lacks them).
- [x] F7 — AI tutor chat: `POST /api/chat` {messages: [{role user|assistant, content}]} →
      {reply} (no DB; 422 `invalid_chat` unless the last message is the learner's, 502/503 as
      elsewhere), `AIProvider.chat()` + Gemini multi-turn contents. Frontend: "💬 Sor" floating
      button → non-modal side panel on every page (full screen on phones), suggestions, Enter
      sends, retry after AI errors, "Yeni sohbet", conversation kept in localStorage (last 50),
      tiny Markdown renderer (**bold**, "- " bullets). Verified with real Gemini (~5 s).
- [x] AUTH — `User`, `AuthSession` (migration 0006: existing data → user `admin`, id 1, no
      password; FKs on documents/learning_sessions/user_vocabulary_progress, documents.user_id
      NOT NULL). `POST /api/auth/login` (HttpOnly SameSite=Lax cookie, `SESSION_COOKIE_SECURE`
      for HTTPS), `POST /api/auth/logout`, `GET /api/auth/me`; 401 `not_authenticated` /
      `invalid_credentials`, 429 `too_many_login_attempts` (5 per username / 20 per client in
      15 min). CLI: create-user, set-password (ends sessions), rename-user, list-users, check.
      Frontend: login page instead of the app while logged out, user + "Çıkış" in the header,
      any 401 returns to the login page, logout clears cached data and the chat history.
      Migration verified on a copy of the real database (upgrade/downgrade/upgrade, no drift).
- [x] DEPLOY — Fly.io app `spektrum-kelime` (fra, `fly.toml`: shared-cpu-1x 512 MB,
      auto stop/start, volume `uploads` → /data/uploads, 30-day snapshots,
      `release_command = "alembic upgrade head"`), PostgreSQL on Neon (direct endpoint;
      `config.use_psycopg_driver` turns postgres:// URLs into postgresql+psycopg://). Root
      `Dockerfile` + `docker-entrypoint.sh` (chowns the volume, drops to user `app`, sets
      HOME=/tmp so libpq does not trip over /root/.postgresql). Fly secrets: DATABASE_URL,
      GEMINI_API_KEY. `.github/workflows/deploy.yml`: tests → `flyctl deploy --remote-only`
      on push to main (secret FLY_API_TOKEN, variable FLY_DEPLOY=true) → health check. Local
      data (users, 738 items, progress) restored into Neon; the PDF copied to the volume.
- [x] AI SETTINGS — `UserAISettings` (migration 0007), `GET/PUT/DELETE /api/ai-settings`
      (key never returned, only `api_key_hint`; omitted key = keep the saved one for the same
      provider/URL), `POST /api/ai-settings/models` (list models with the entered or saved
      key), `POST /api/ai-settings/test` (one tiny chat, nothing saved). AI features answer
      503 `ai_not_configured` until a user saves settings. Frontend `/settings` (header
      "⚙️ Ayarlar"): provider, base URL (compatible), key, model with fetched suggestions,
      test / save / delete; the chat panel links there when nothing is configured. Verified
      with real Gemini (models, test, chat, chapter detection, answer evaluation); OpenAI and
      Anthropic only against fake SDK clients (no keys available).
- [x] Self-hosting — `start.ps1` (one command), backend serves `frontend/dist` when
      `FRONTEND_DIST_DIR` is set, Postgres published on 127.0.0.1 only with
      `restart: unless-stopped`, `DATABASE_URL` → 127.0.0.1, root README with Tailscale access
      (firewall rule limited to 100.64.0.0/10), autostart and backups.
