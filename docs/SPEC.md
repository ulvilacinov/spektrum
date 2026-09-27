I want to build an AI-assisted German vocabulary learning web application.

Act as the senior software engineer responsible for implementing the project with me.

IMPORTANT:
- Build the project incrementally.
- Do not jump ahead.
- Do not generate frontend code yet.
- Do not replace previously created architecture without a clear technical reason.
- Keep all code compatible with code created in previous steps.
- When creating or modifying files, always show the exact file path.
- Prefer clean, production-friendly code over shortcuts.
- Do not overengineer the MVP.
- If an architectural decision is needed, briefly explain it and choose a sensible default instead of stopping unnecessarily.
- Every implementation step should leave the application in a runnable state.

==================================================
PROJECT GOAL
==================================================

The application allows a user to upload a PDF containing German vocabulary,
phrases and expressions.

The system should:

1. Upload the PDF.
2. Extract text page by page.
3. Detect chapters such as:
   Kapitel 1
   Kapitel 2
   Kapitel 3
4. Extract vocabulary items belonging to each chapter.
5. Store the structured vocabulary in PostgreSQL.
6. Allow the user later to study vocabulary in batches such as:
   5 / 10 / 20 words.
7. Quiz the user.
8. Detect mistakes.
9. Mark difficult vocabulary as Weak.
10. Repeat weak vocabulary.
11. Mark vocabulary as Mastered after repeated correct answers.
12. Continue with the next vocabulary batch.

The learning workflow is:

PDF
→ Chapter
→ Learn 5/10/20 vocabulary items
→ Quiz
→ Evaluate answers
→ Explain mistakes
→ Weak words
→ Review weak words
→ Mastered
→ Next batch

==================================================
TECH STACK
==================================================

Backend:
- Python 3.12
- FastAPI
- Uvicorn

Validation / schemas:
- Pydantic v2

Database:
- PostgreSQL
- SQLAlchemy 2.x
- Alembic

PDF parsing:
- PyMuPDF (pymupdf)

AI:
- Provider abstraction
- First implementation: Gemini API

Testing:
- pytest

Configuration:
- pydantic-settings
- .env

Frontend:
- React
- TypeScript

IMPORTANT:
Do NOT implement the frontend yet.

The frontend will be developed only after the first backend milestone is working.

==================================================
BACKEND ARCHITECTURE
==================================================

Use a structure similar to:

backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │
│   ├── schemas/
│   │
│   ├── repositories/
│   │
│   ├── services/
│   │   ├── pdf/
│   │   ├── ai/
│   │   ├── documents/
│   │   └── learning/
│   │
│   └── domain/
│       ├── enums.py
│       └── entities.py
│
├── alembic/
├── tests/
├── uploads/
├── pyproject.toml
├── alembic.ini
├── .env.example
└── README.md

Keep API, domain logic, persistence and external services separated.

Do not put business logic directly inside FastAPI route handlers.

==================================================
CORE DATABASE MODELS
==================================================

Create the following models.

DOCUMENT

Document
- id
- user_id nullable for MVP
- file_name
- original_file_name
- storage_path
- status
- uploaded_at
- processed_at nullable
- error_message nullable

DocumentStatus:
- uploaded
- parsing
- parsed
- failed


CHAPTER

Chapter
- id
- document_id
- title
- chapter_number
- order
- source_start_page
- source_end_page


VOCABULARY ITEM

VocabularyItem
- id
- chapter_id

- german
- turkish

- item_type
- article nullable

- base_verb nullable
- prateritum nullable
- perfekt nullable

- preposition nullable
- grammatical_case nullable

- example_german nullable
- example_turkish nullable

- source_text nullable
- source_page nullable

- order


VocabularyItemType:
- word
- noun
- verb
- phrase
- expression
- grammar_pattern


USER VOCABULARY PROGRESS

UserVocabularyProgress
- id
- user_id
- vocabulary_item_id

- status

- seen_count
- correct_count
- wrong_count
- consecutive_correct

- mastery_score

- last_seen_at nullable
- next_review_at nullable


VocabularyStatus:
- new
- learning
- weak
- mastered


LEARNING SESSION

LearningSession
- id
- user_id
- chapter_id
- batch_size
- started_at
- completed_at nullable
- correct_count
- wrong_count


QUIZ QUESTION

QuizQuestion
- id
- learning_session_id
- vocabulary_item_id
- question_type
- question
- expected_answer
- user_answer nullable
- is_correct nullable
- ai_feedback nullable


QuestionType:
- german_to_turkish
- turkish_to_german
- fill_blank
- sentence_translation
- verb_conjugation
- article
- preposition
- free_sentence

==================================================
VOCABULARY STRUCTURE
==================================================

Example:

Source:

an einer Konferenz teilnehmen

Store it approximately as:

{
  "german": "an einer Konferenz teilnehmen",
  "turkish": "bir konferansa katılmak",
  "item_type": "verb",
  "base_verb": "teilnehmen",
  "preposition": "an",
  "grammatical_case": "Dativ",
  "example_german": "Ich nehme morgen an einer Konferenz teil.",
  "example_turkish": "Yarın bir konferansa katılıyorum."
}

Another example:

{
  "german": "die Veranstaltung",
  "turkish": "etkinlik",
  "item_type": "noun",
  "article": "die",
  "example_german": "Die Veranstaltung beginnt um 18 Uhr.",
  "example_turkish": "Etkinlik saat 18'de başlıyor."
}

==================================================
PDF PROCESSING FLOW
==================================================

The processing pipeline should be:

PDF upload
→ save file
→ extract page-by-page text
→ preserve page numbers
→ detect chapters
→ send relevant text sections to AI
→ extract structured vocabulary
→ validate AI output using Pydantic
→ store Chapters and VocabularyItems in PostgreSQL

Do NOT send the PDF to AI on every request.

The document should be processed once.

After processing, normal learning operations should use PostgreSQL.

Preserve the original source page and source text whenever possible.

==================================================
AI ARCHITECTURE
==================================================

The application must NOT depend directly on Gemini throughout the codebase.

Create an abstraction such as:

AIProvider

with methods similar to:

analyze_document(...)
extract_chapters(...)
extract_vocabulary(...)
evaluate_answer(...)
generate_example(...)

Create:

GeminiAIProvider

as the first implementation.

The provider should be replaceable later by:
- OpenAI
- Anthropic
- local models
- another provider

without changing business logic.

==================================================
AI STRUCTURED OUTPUT
==================================================

Never rely on free-form AI text for document parsing.

Use structured JSON output validated by Pydantic.

For vocabulary extraction, return a structure similar to:

{
  "chapter_title": "Kapitel 1",
  "sections": [
    {
      "name": "Alltag",
      "items": [
        {
          "german": "im Stau stehen",
          "turkish": "trafikte kalmak",
          "item_type": "phrase",
          "article": null,
          "base_verb": "stehen",
          "prateritum": null,
          "perfekt": null,
          "preposition": null,
          "grammatical_case": null,
          "example_german": "Ich stehe jeden Morgen im Stau.",
          "example_turkish": "Her sabah trafikte kalıyorum.",
          "source_text": "im Stau stehen",
          "source_page": 1
        }
      ]
    }
  ]
}

Very important:

The AI may generate:
- example sentences
- explanations
- translations when required

But vocabulary items themselves must originate from the uploaded PDF.

Do not silently invent additional vocabulary.

==================================================
ANSWER EVALUATION
==================================================

Answer checking will eventually use three levels:

1. Exact match
2. Normalized deterministic comparison
3. AI evaluation only when necessary

Normalization should handle things such as:
- whitespace
- capitalization where appropriate
- punctuation
- harmless formatting differences

Simple answers should NOT require an AI call.

Example:

Expected:
die Veranstaltung

User:
die Veranstaltung

→ deterministic validation

For free sentence answers:

Expected:
Ich möchte nicht immer das Gleiche machen.

User:
Ich möchte nicht immer gleich machen.

→ AI evaluation

AI evaluation should return structured output:

{
  "is_correct": false,
  "score": 0.75,
  "corrected_answer": "Ich möchte nicht immer das Gleiche machen.",
  "explanation": "Burada 'das Gleiche machen' kalıbı kullanılır.",
  "error_type": "vocabulary_usage"
}

Error types should include:

- article
- case
- preposition
- word_order
- verb_conjugation
- spelling
- vocabulary_usage
- meaning
- grammar

AI feedback for the learner should normally be in Turkish.

==================================================
LEARNING LOGIC
==================================================

For MVP use a simple progression system.

Initial state:
new

After first study:
learning

Wrong answer:
weak

Correct once:
learning

Correct twice consecutively:
mastered

This logic should be isolated in a service so we can replace it later with
spaced repetition.

Do not hard-code progression logic inside API routes.

==================================================
FUTURE API DESIGN
==================================================

Eventually we expect routes similar to:

POST /api/documents
GET /api/documents
GET /api/documents/{id}

POST /api/documents/{id}/analyze

GET /api/documents/{id}/chapters

GET /api/chapters/{id}
GET /api/chapters/{id}/vocabulary

POST /api/learning-sessions
GET /api/learning-sessions/{id}/items

POST /api/learning-sessions/{id}/quiz

POST /api/quiz/{question_id}/answer

GET /api/progress
GET /api/review/weak

But do not implement all of these immediately.

==================================================
MVP DEFINITION OF DONE
==================================================

The full future MVP workflow is:

1. User uploads a German vocabulary PDF.

2. Backend extracts pages.

3. AI detects:
   Kapitel 1
   Kapitel 2
   Kapitel 3
   etc.

4. Vocabulary items are extracted.

5. Chapters and vocabulary items are stored in PostgreSQL.

6. User selects Kapitel 1.

7. User chooses:
   5 / 10 / 20 Wörter lernen.

8. Learning screen displays vocabulary.

9. Quiz is generated.

10. Answers are evaluated.

11. Wrong vocabulary becomes Weak.

12. Weak vocabulary is reviewed.

13. After two consecutive correct answers it becomes Mastered.

14. Next vocabulary batch is unlocked.

==================================================
FIRST DEVELOPMENT MILESTONE
==================================================

For now implement ONLY this milestone:

PDF upload
→ save file
→ extract text page by page
→ analyze document
→ detect chapters
→ extract vocabulary
→ store Chapter and VocabularyItem records in PostgreSQL
→ retrieve them through FastAPI / Swagger

The milestone is complete when this works:

POST /api/documents

Upload a PDF.

Then:

POST /api/documents/{id}/analyze

Then:

GET /api/documents/{id}/chapters

returns something similar to:

[
  {
    "chapter_number": 1,
    "title": "Kapitel 1",
    "vocabulary_count": 68
  }
]

And:

GET /api/chapters/{id}/vocabulary

returns real extracted vocabulary records.

==================================================
HOW TO START
==================================================

Start with STEP 1 only.

In STEP 1:

1. Define the initial folder/project structure.
2. Create pyproject.toml.
3. List and configure required dependencies.
4. Create FastAPI application bootstrap.
5. Add configuration using pydantic-settings.
6. Configure SQLAlchemy PostgreSQL connection.
7. Configure Alembic.
8. Create the initial domain/database models:
   - Document
   - Chapter
   - VocabularyItem
9. Create the first migration.
10. Add a basic health endpoint.
11. Provide commands to run the application locally.

Do NOT implement:
- Gemini integration yet
- PDF extraction yet
- learning sessions yet
- quizzes yet
- React frontend yet

At the end of STEP 1 provide:

- final project tree
- complete content of every created file
- commands to install dependencies
- commands to start PostgreSQL if Docker is used
- migration commands
- command to run FastAPI
- a short checklist to verify STEP 1 works

After STEP 1 stop and wait for me before continuing to STEP 2.