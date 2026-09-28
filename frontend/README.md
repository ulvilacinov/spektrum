# German Vocabulary Trainer — Frontend

React + TypeScript (Vite) client for the backend in `../backend`. The UI is in Turkish.

Current state: **F1** — document list, PDF upload, starting the analysis.

## Requirements

- Node.js 20+ (developed with 24)
- The backend running on `http://127.0.0.1:8000` (see `../backend/README.md`)

## Run

```bash
npm install
npm run dev          # http://localhost:5173
```

Vite proxies `/api` to the backend (`VITE_BACKEND_URL`, default `http://127.0.0.1:8000`), so
the browser talks to one origin and the backend needs no CORS setup.

## Checks

```bash
npm test             # Vitest + Testing Library (fetch is faked, no backend needed)
npm run lint         # oxlint
npm run build        # type-check + production build
```

## API types

`src/api/schema.d.ts` is generated from the backend's OpenAPI schema and committed, so the
frontend builds without a running backend. Regenerate it after every API change:

```bash
npm run gen:api      # needs the backend on 127.0.0.1:8000
```

TypeScript is pinned to 5.9 because `openapi-typescript` does not support TypeScript 6 yet.

## Layout

- `src/api/` — typed client (`openapi-fetch`), Turkish error messages, TanStack Query hooks.
- `src/pages/` — one component per route; `src/router.tsx` lists the routes.
- `src/components/` — reusable UI pieces.
- `src/test/` — test setup, `renderRoute()` and a fake `fetch` (`mockApi`).
