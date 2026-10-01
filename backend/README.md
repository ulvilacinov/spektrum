# German Vocabulary Trainer — Backend

FastAPI backend for an AI-assisted German → Turkish vocabulary learning app.
Current state: **STEP 8**, backend MVP complete: PDF upload, AI chapter and vocabulary
extraction, learning sessions, quizzes, answer evaluation with Turkish feedback, weak-word
review, progress and batch unlocking.

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

## Accounts

Every endpoint except `/api/health` and `/api/auth/login` needs a login. There is no public
sign-up; accounts are managed from the command line:

```bash
python -m app.cli create-user anna        # asks for the password (min. 8 characters)
python -m app.cli set-password anna       # also logs the user out everywhere
python -m app.cli rename-user anna anna.k
python -m app.cli list-users
```

Data from before accounts existed belongs to the user `admin` created by migration 0006; it
has no password until you run `python -m app.cli set-password admin`.

| Method | Path | |
|---|---|---|
| POST | `/api/auth/login` | {username, password} → sets the HttpOnly session cookie (30 days, extended while used). 401 `invalid_credentials`; 429 `too_many_login_attempts` after 5 failures per username (or 20 per client) in 15 minutes. |
| POST | `/api/auth/logout` | Ends the session and clears the cookie (204). |
| GET | `/api/auth/me` | The logged-in user, or 401 `not_authenticated`. |

Passwords are hashed with scrypt; only a SHA-256 hash of the session token is stored.
Set `SESSION_COOKIE_SECURE=true` when the app is served over HTTPS.

## Documents API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/documents` | Upload a PDF (`multipart/form-data`, field `file`). Returns 201. |
| GET | `/api/documents?limit=50&offset=0` | List documents, newest first. |
| GET | `/api/documents/{id}` | Get one document. |
| POST | `/api/documents/{id}/analyze?force=false` | Detect chapters and extract vocabulary with the AI (synchronous). |
| GET | `/api/documents/{id}/chapters` | Chapters in reading order with `vocabulary_count` (`[]` before analysis). |
| GET | `/api/chapters/{id}/vocabulary` | Vocabulary items of a chapter in PDF order. |

```bash
curl -F "file=@Wortschatz.pdf;type=application/pdf" http://localhost:8000/api/documents
```

Uploads are limited to `MAX_UPLOAD_SIZE_MB` and must be readable, unencrypted PDFs. Files are
stored as `UPLOAD_DIR/<uuid>.pdf`; the original name is kept in the database. Errors use the
shape `{"error": {"code", "message", "details"}}` (415 wrong type, 413 too large, 422 invalid PDF).

### Analysis

Every user chooses the AI on the settings page (`/settings`, or the API below): Google
Gemini, OpenAI, Anthropic Claude, or any OpenAI-compatible service (DeepSeek, OpenRouter,
Groq, ... with its https base URL), plus their own API key and model. Keys are stored
encrypted with `SECRET_KEY`. Until a user saves settings, analysis, open-answer evaluation
and chat answer 503 `ai_not_configured`.

| Method | Path | |
|---|---|---|
| GET | `/api/ai-settings` | Provider, model, base URL and the key's last characters (never the key). |
| PUT | `/api/ai-settings` | {provider, model, base_url?, api_key?}; without `api_key` the saved key is kept (same provider/URL). |
| DELETE | `/api/ai-settings` | Forget the key (AI features off). |
| POST | `/api/ai-settings/models` | Models the entered or saved key can use. |
| POST | `/api/ai-settings/test` | One tiny request with these values; nothing is saved. |

With Gemini's free tier keep `AI_REQUESTS_PER_MINUTE=5`: requests are then spaced 12 s apart,
so a 12-chapter book takes about 3 minutes. Rate-limit responses (429) are waited out;
an exhausted daily quota fails the analysis with a clear error.
`POST /api/documents/{id}/analyze` then:

1. extracts the text of every page (1-based page numbers),
2. asks the AI for the chapters ("Kapitel N" headings or running headers),
3. sends each chapter's pages (in chunks of `AI_MAX_PAGES_PER_REQUEST`, up to
   `AI_MAX_CONCURRENCY` requests in parallel) for structured vocabulary extraction,
4. keeps only items whose `source_text` really occurs on the page (others are counted in
   `rejected_item_count` and logged), and
5. stores chapters and vocabulary in one transaction; the document becomes `parsed`.

On failure the document becomes `failed` with `error_message` and can be analyzed again.
An already `parsed` document needs `?force=true`, which replaces its chapters and
therefore also deletes the learning sessions and progress of that document.
Status codes: 409 already parsed / in progress, 422 PDF without text layer,
502 AI error or invalid AI output, 503 AI not configured.

## Learning API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/learning-sessions` | `{"chapter_id": 1, "batch_size": 10, "mode": "new"}`: start a batch (size 1-100, default 10). `mode=review` picks studied but unmastered words, weak ones first. |
| GET | `/api/learning-sessions/{id}` | The session with its chapter title and document id. |
| GET | `/api/learning-sessions/{id}/items` | The batch's words in order, each with its learning status. |
| POST | `/api/learning-sessions/{id}/quiz` | Create the batch's quiz (201), or return the existing one (200). |
| POST | `/api/quiz/{question_id}/answer` | `{"answer": "die"}`: evaluate once, return Turkish feedback and the word's new status. |
| GET | `/api/progress?document_id=` | Per chapter: new/learning/weak/mastered counts, mastery ratio, whether a new batch or a review can start. |
| GET | `/api/review/weak?chapter_id=` | Weak words with the latest mistake and its Turkish explanation. |

Starting a session marks its words as studied (`new` → `learning`). When every word of the
chapter has been studied the API answers 409 `no_new_vocabulary`. Status changes are made only
by `ProgressionPolicy` (`app/services/learning/progression.py`): a wrong answer makes a word
`weak`, two correct answers in a row make it `mastered`. Every request acts as the logged-in
user (see Accounts); documents, sessions and progress belong to that user.

Quizzes are built without AI from the stored vocabulary data: one question per word, its
type chosen (weighted, reproducibly per session) from translation in both directions,
article, preposition, verb conjugation and sentence translation. Question texts are in
Turkish; the expected answers are stored but never returned before the question is answered.

The learning cycle: start a batch (`mode=new`) → quiz → wrong answers make words `weak` →
review them (`mode=review`) → two correct answers in a row make a word `mastered` → once
every studied word of the chapter is mastered, the next batch unlocks (before that,
`mode=new` answers 409 `batch_locked`).

Answers are checked in three steps: an exact match, then a normalized comparison (case,
punctuation, alternatives written with "/", optional parts in parentheses, Turkish letters
typed without diacritics, German ae/oe/ue/ss), and only then the AI for open questions
(translations). Closed questions (article, preposition, verb form) never call the AI. If the
AI fails, nothing is stored and the learner can answer again.

### Milestone check

```bash
curl -F "file=@Wortschatz.pdf;type=application/pdf" http://localhost:8000/api/documents
curl -X POST http://localhost:8000/api/documents/1/analyze
curl http://localhost:8000/api/documents/1/chapters     # [{chapter_number, title, vocabulary_count, ...}]
curl http://localhost:8000/api/chapters/1/vocabulary    # extracted items with examples
```

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
- `app/repositories` — database access; never commits.
- `app/services/pdf` — PyMuPDF text extraction (page by page, 1-based page numbers).
- `app/services/documents` — upload validation, file storage, document analysis
  (chapter planning, vocabulary grounding).
- `app/services/ai` — `AIProvider` interface, Gemini / OpenAI / Anthropic implementations, prompts, output schemas.
- `app/services/ai_settings` — per-user provider, model and encrypted API key.
