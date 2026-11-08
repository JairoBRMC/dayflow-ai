# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Dayflow AI is a personal task/goal planning assistant with an AI chat that helps plan the user's day (function calling + RAG over the user's tasks/events, planned). The project is in early, active development: the backend (auth, `Task`/`Event`/`Conversation` CRUD, Groq-backed chat) is well along; the frontend has its project setup, API client, and authentication screens, with the actual task/calendar/chat UI still to come.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL 16 (via Docker), accessed with SQLAlchemy 2.x
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Auth:** JWT (access + refresh) via PyJWT, password hashing via passlib (`CryptContext(schemes=["bcrypt"])`)
- **Frontend:** React 19 + TypeScript, built with Vite, `react-router-dom` for routing, `axios` for HTTP — see [Frontend architecture](#frontend-architecture) below
- **AI:** Groq (`groq` Python client) for chat completions — function calling and RAG over the user's own tasks/events not implemented yet
- **Testing:** pytest + FastAPI's `TestClient` (backend); no frontend tests yet
- **Infra:** Docker — two Postgres services in [docker-compose.yml](docker-compose.yml), `db` (dev, port 5433) and `db_test` (pytest, port 5434); GitHub Actions planned

## Commands

All backend commands run from `backend/` with the virtualenv (`backend/venv`) activated.

```
# Start both Postgres instances -- dev (db) and test (db_test) -- from repo root
docker-compose up -d

# Run the API with reload
uvicorn main:app --reload

# Create a new migration from model changes (applies to the dev DB, DATABASE_URL)
alembic revision --autogenerate -m "descripcion en español"

# Apply migrations to the dev DB
alembic upgrade head

# Run the test suite -- requires db_test up; conftest.py migrates it to head
# automatically, so there's no separate "alembic upgrade" step for tests
pytest

# Run a single test
pytest tests/test_tasks.py::test_get_task_not_found_returns_404
```

Frontend commands run from `frontend/`:

```
# Install dependencies (first time, or after pulling a package.json change)
npm install

# Dev server with HMR, defaults to http://localhost:5173
npm run dev

# Type-check (tsc -b) then production build
npm run build

# Lint (flat eslint.config.js: typescript-eslint + react-hooks + react-refresh)
npm run lint
```

There is no backend lint or CI setup yet, and no frontend test runner yet either — those commands don't exist in this repo currently.

`.env` needs a `SECRET_KEY` (JWT signing secret) alongside `DATABASE_URL` and `TEST_DATABASE_URL` — generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. Like `DATABASE_URL`, `database.py`/`auth.py` raise a `RuntimeError` on startup if it's missing rather than failing later with a confusing error; `tests/conftest.py` does the same for `TEST_DATABASE_URL`.

`requirements.txt` pins `bcrypt==4.0.1`: passlib 1.7.4 (unmaintained) reads `bcrypt.__about__.__version__` to detect the backend, which `bcrypt>=4.1` removed, so anything newer breaks `CryptContext(schemes=["bcrypt"])` at the first `.hash()`/`.verify()` call. Don't bump `bcrypt` past `4.0.x` without also moving off passlib.

`GROQ_API_KEY` is checked lazily (first call to `groq_client.get_chat_completion`, not at import time) and only `.env`, not `.env.example`'s placeholder, needs a real value — deliberately different from `DATABASE_URL`/`SECRET_KEY`'s eager, import-time `RuntimeError`. Those two are needed for every request; a missing Groq key should only break `POST /conversations/{id}/chat`, not the entire app (and every pytest run) for a contributor who isn't touching chat. `GROQ_MODEL` is optional (defaults to `openai/gpt-oss-20b`); Groq's available-model list has shifted before (it dropped the Llama 3.x models this project originally used) — if chat starts returning `404 model_not_found`, run `Groq(api_key=...).models.list()` to see what's currently available for the key in use and update the default or `.env`'s `GROQ_MODEL`.

`main.py` adds `CORSMiddleware` with origins from `CORS_ORIGINS` in `.env` (comma-separated, defaults to `http://localhost:5173,http://127.0.0.1:5173`). This has to be there for the frontend to work at all: CORS is enforced by the browser, not visible to `curl` or a backend-only pytest run, so it's an easy thing to add the frontend code for and then discover is still broken only once it's running in an actual browser. If Vite picks a different port (it prints the one it's actually using when it can't get 5173), add it to `CORS_ORIGINS`.

**Tests run against their own Postgres, never the dev database.** `docker-compose.yml` defines a second service, `db_test` (port `5434`, db `dayflow_test_db`), and `tests/conftest.py` points at it via `TEST_DATABASE_URL`, not `DATABASE_URL`. A session-scoped autouse fixture in `conftest.py` runs `alembic upgrade head` against `TEST_DATABASE_URL` before the first test (temporarily reassigning the `DATABASE_URL` env var just for that one call, since `alembic/env.py` reads it directly — the dev DB is never touched), so the test DB goes from empty to the full schema automatically; there's no manual migration step before running `pytest`. `main.py`'s `get_db` dependency is overridden (`app.dependency_overrides[get_db]`) to hand out sessions bound to the test engine instead, so the app code under test is unmodified. Cleanup between tests is still explicit create-via-API-then-delete-in-teardown (see the fixtures in `tests/conftest.py`), not transaction-per-test-with-rollback: the suite's actual cost is bcrypt hashing (~100ms+ per register/login), not database I/O, so a transactional-rollback harness would add real complexity (wrapping `get_db()` in nested `SAVEPOINT`s so the app's own `db.commit()` calls don't break the rollback) for a speedup that wouldn't show up anywhere. Revisit that trade-off if the suite grows enough that DB cleanup, not hashing, becomes the bottleneck.

## Architecture

The backend is a flat, single-package FastAPI app (no `app/` src layout, no routers module yet) — everything currently lives directly under `backend/`:

- [database.py](backend/database.py) — loads `DATABASE_URL` from `.env` (raises a clear `RuntimeError` if it's missing), creates the SQLAlchemy `engine`/`SessionLocal`, defines the declarative `Base`, and exposes the `get_db()` dependency used for request-scoped sessions.
- [models.py](backend/models.py) — SQLAlchemy ORM models: `User`, `Task`, `Event`, `Conversation`, `ChatMessage`.
- [schemas.py](backend/schemas.py) — Pydantic request/response models, kept separate from the ORM models in `models.py`: a `*Create`/`*Update`/`*Out` trio per entity (`TaskCreate`/`TaskUpdate`/`TaskOut`, `EventCreate`/`EventUpdate`/`EventOut`), plus `UserCreate`/`UserOut`, `Token`, `RefreshRequest` for auth, and `ConversationCreate`/`ConversationOut`/`ConversationDetail`/`MessageOut` for chat. `*Out` schemas use `model_config = ConfigDict(from_attributes=True)` so they can be built straight from the ORM instance; `*Update` schemas have every field optional, for partial updates.
- [auth.py](backend/auth.py) — password hashing (`hash_password`/`verify_password` via passlib), JWT creation/decoding (`create_access_token`, `create_refresh_token`, `decode_token`), and the `get_current_user` dependency that every protected endpoint depends on. Reads `SECRET_KEY` from `.env` the same way `database.py` reads `DATABASE_URL` (`RuntimeError` if missing).
- [groq_client.py](backend/groq_client.py) — the only module that talks to Groq. `get_chat_completion(messages)` takes an OpenAI-shaped message list (`[{"role": ..., "content": ...}]`) and returns the assistant's reply string. Client construction (and the `GROQ_API_KEY` check) is lazy, behind `@lru_cache`, not at import time — see the Commands section above for why.
- [main.py](backend/main.py) — the FastAPI app and all endpoints (no routers module yet, everything in one file).
- [alembic/env.py](backend/alembic/env.py) — reads `DATABASE_URL` from `.env` itself and points `target_metadata` at `Base.metadata`; every new model must be imported here (next to the existing imports) or `--autogenerate` won't see it.
- [tests/conftest.py](backend/tests/conftest.py) — points the app at the dedicated test database and migrates it (see Commands above), then defines shared fixtures: `auth_headers`/`registered_email` (one test user, via `registered_user`) and `other_user_headers` (a second, independent user, for cross-user isolation tests). Both clean up their user in teardown; `ondelete="CASCADE"` on `Task.user_id`/`Event.user_id`/`Conversation.user_id`/`ChatMessage.conversation_id` takes their rows with them.
- [tests/test_tasks.py](backend/tests/test_tasks.py), [tests/test_events.py](backend/tests/test_events.py), [tests/test_auth.py](backend/tests/test_auth.py), [tests/test_conversations.py](backend/tests/test_conversations.py), [tests/test_chat.py](backend/tests/test_chat.py) — pytest suites, one file per entity/concern. `test_chat.py` monkeypatches `main.get_chat_completion` (a `fake_groq` fixture) instead of calling the real Groq API: it's a paid, rate-limited, network-dependent external service, unlike the dedicated Postgres the rest of the suite happily hits for real — mocking it keeps the suite fast, free, and deterministic. Groq connectivity itself is verified manually (e.g. a one-off script calling `groq_client.get_chat_completion`), not by the automated suite.

Data model conventions (see [backend/README.md](backend/README.md) for the full planned schema and the ER diagram at `backend/Docs/er-diagram.png`):
- Primary keys are UUIDs (`sqlalchemy.dialects.postgresql.UUID`, `default=uuid.uuid4`), not autoincrement ints.
- Enum-like fields (`status`, `priority`, `role`) are plain `String` columns at the DB level — the allowed values live as a comment next to the column, not a DB/Python enum type. Validation instead happens at the API boundary: `schemas.py` defines `Priority`/`TaskStatus` as `typing.Literal` types and reuses them in both request bodies and query params, so an invalid value (`priority=urgentisimo`) is rejected with FastAPI's automatic `422` before it ever reaches the DB.
- `created_at` uses `server_default=func.now()` rather than an application-side default.
- `Task.user_id`/`Event.user_id` are `nullable=True` at the DB level even though every row created through the API always has one — this was a deliberate, non-destructive choice when the FK was added on top of rows that predated auth, rather than deleting that data or backfilling it to a placeholder user. A `NULL` `user_id` never matches `model.user_id == current_user.id`, so old rows just become permanently unreachable through the API instead of raising an integrity error.
- Endpoints that take a resource id look it up with a shared `_get_owned_or_404(model, obj_id, owner_id, db)` helper ([main.py](backend/main.py)), generic over the ORM model, which filters by both `id` and `user_id` in one query and raises `HTTPException(status_code=404, ...)` if either doesn't match — used by `GET`/`PUT`/`DELETE` on both `/tasks/{id}` and `/events/{id}`. Returning `404` (never `403`) for "belongs to someone else" is deliberate: it doesn't let a caller distinguish "doesn't exist" from "exists but isn't yours".
- `PUT` endpoints are partial updates in practice: `*Update` schema fields all default to `None`, and the handler applies `update.model_dump(exclude_unset=True)` so only fields actually present in the request body overwrite the row — a field omitted from the JSON body is left untouched rather than being reset to `None`.
- `Event` additionally validates `end_time > start_time`: on create, a Pydantic `model_validator(mode="after")` on `EventCreate` rejects an invalid range with `422` before a row is ever built; on update, since `EventUpdate` allows changing just one of the two timestamps, the check instead happens in the `PUT /events/{id}` handler itself, after merging the update into the loaded `Event`, so it catches a bad combination no matter which field changed.
- Auth uses two JWTs, not one: an access token (30 min, `type: "access"`, required by `get_current_user`) and a refresh token (7 days, `type: "refresh"`, only accepted by `POST /auth/refresh`). Both carry the user id as `sub` and are signed with the same `SECRET_KEY`/`HS256`; `decode_token(token, expected_type=...)` checks the `type` claim so an access token can't be replayed as a refresh token (and vice versa) — see `test_refresh_rejects_an_access_token_as_refresh_token`. There's no server-side token store, so a refresh token can't be revoked before it expires (no logout/blacklist endpoint yet).
- `POST /auth/login` takes `OAuth2PasswordRequestForm` (form-encoded `username`/`password`, `username` holding the email) rather than a JSON body, and `get_current_user` uses `OAuth2PasswordBearer(tokenUrl="auth/login")` — matching FastAPI's standard security tutorial shape means the `/docs` "Authorize" button works out of the box for manual testing. Every other endpoint (including `/auth/register` and `/auth/refresh`) takes a plain JSON body like the rest of the API.
- `GET /auth/me` exists purely for the frontend: `/auth/login`/`/auth/refresh` return only tokens, no user info, so there was no way for `AuthContext` to know *who* is logged in (email, id) from a stored `access_token` alone without either decoding the JWT client-side or adding this endpoint. It's a one-line reuse of `get_current_user` + `UserOut`.
- `ChatMessage` has no `user_id` of its own — ownership is inherited through `ChatMessage.conversation_id → Conversation.user_id`, since a message only ever makes sense as part of one user's conversation. `Conversation.user_id` is `NOT NULL` (unlike `Task`/`Event`'s `user_id`): it's a brand-new table with no pre-auth rows to accommodate, so there was no reason to make it nullable.
- `GET /conversations` (list) returns `ConversationOut` — no messages — while `GET /conversations/{id}` (detail) returns `ConversationDetail`, which adds a `messages: list[MessageOut]` field populated by a second, explicit query (`ChatMessage` filtered by `conversation_id`, ordered by `created_at`). Deliberately not a SQLAlchemy `relationship()`/eager-load: listing conversations would otherwise pull every message of every conversation just to discard them, and the codebase doesn't use ORM relationships anywhere else either (every other query is explicit, e.g. `_get_owned_or_404`, the `Task`/`Event` list filters).
- `POST /conversations/{id}/chat` is the only way `ChatMessage` rows get created. It: saves the user's message, re-reads the *entire* conversation (including the message just saved) ordered by `created_at`, sends that full list to `get_chat_completion` so Groq has the whole conversation as context (not just the latest message), then saves and returns the assistant's reply as a `MessageOut`. A `groq.APIError` from that call is caught and turned into `HTTPException(502)` — the user's message stays saved either way, only the assistant's reply is missing, so retrying the same conversation doesn't duplicate the user's turn.
- `tests/test_conversations.py` still inserts `ChatMessage` rows directly via `TestSessionLocal` for cases that predate the chat endpoint (checking `GET /conversations/{id}` serializes/orders messages it didn't create itself) — `tests/test_chat.py` covers the endpoint that actually creates them.

Planned beyond `User`/`Task`/`Event`/`Conversation`/`ChatMessage`: function calling (`create_task`/`update_task`/`list_tasks`-shaped tools Groq can invoke from chat) and RAG (pulling the user's real tasks/events into context before responding), plus a future `Goal` entity to group tasks — see [backend/README.md](backend/README.md) and the root [TO-DO.txt](TO-DO.txt) for the full breakdown.

## Frontend architecture

The frontend is being built in phases (see the root [TO-DO.txt](TO-DO.txt): F1 setup, F2 API layer, F3 auth — done; F4 tasks, F5 calendar, F6 chat, F7 polish — not yet). `src/` layout:

- [src/api/client.ts](frontend/src/api/client.ts) — the shared `axios` instance every API call goes through. A request interceptor attaches `Authorization: Bearer <access_token>` from `localStorage`. A response interceptor catches a `401`, refreshes via `POST /auth/refresh` (using a bare `axios.post`, not `apiClient`, so the refresh call itself can't recurse into this same interceptor), stores the new access *and* refresh token (the backend rotates both on every refresh), retries the original request once (`_retry` flag prevents a loop), and otherwise clears both tokens and hard-redirects to `/login`. Concurrent `401`s share one in-flight refresh call (`refreshInFlight`) instead of each firing their own `POST /auth/refresh`.
- [src/api/auth.ts](frontend/src/api/auth.ts) — thin wrappers for `/auth/register`, `/auth/login` (builds the `URLSearchParams` form body `/auth/login` expects — see the backend note on `OAuth2PasswordRequestForm` above), and `/auth/me`.
- [src/context/auth-context.ts](frontend/src/context/auth-context.ts), [AuthContext.tsx](frontend/src/context/AuthContext.tsx), [useAuth.ts](frontend/src/context/useAuth.ts) — split into three files instead of one `AuthContext.tsx` exporting both the `AuthProvider` component and the `useAuth` hook: `eslint-plugin-react-refresh`'s `only-export-components` rule wants a file with a component export to export *only* components, since Fast Refresh keys off that. `auth-context.ts` holds the `createContext` call and the `AuthContextValue` type (no component, no hook); `AuthContext.tsx` holds only `AuthProvider`; `useAuth.ts` holds only the `useAuth` hook. `AuthProvider` initializes `isLoading` lazily from whether an `access_token` is already in `localStorage` (not via a synchronous `setState` inside `useEffect` — `eslint-plugin-react-hooks`'s `set-state-in-effect` rule flags that), and if there is one, calls `GET /auth/me` to populate `user`; a stale/expired access token is handled by `client.ts`'s own refresh logic before this call ever fails.
- [src/components/ProtectedRoute.tsx](frontend/src/components/ProtectedRoute.tsx) — redirects to `/login` when `useAuth().user` is `null` once `isLoading` has settled; renders nothing conclusive (a loading message) while it's still checking, so it never flashes a redirect before a valid stored session has had a chance to resolve.
- [src/pages/LoginPage.tsx](frontend/src/pages/LoginPage.tsx), [RegisterPage.tsx](frontend/src/pages/RegisterPage.tsx) — forms calling `useAuth().login`/`.register`. `RegisterPage` calls `register`, which itself calls `/auth/register` then immediately logs in with the same credentials (the register endpoint returns a `UserOut`, not tokens) — so signing up logs you in, no separate "now go log in" step. Both redirect to `/` (via `<Navigate>`) if `useAuth().user` is already set, so a logged-in user can't land back on these forms.
- [src/pages/DashboardPage.tsx](frontend/src/pages/DashboardPage.tsx) — placeholder behind `ProtectedRoute` at `/`, just proving the whole chain works (shows the logged-in email, has a logout button). F4/F5/F6 build the real content here.
- [src/App.tsx](frontend/src/App.tsx) — all routes (`react-router-dom`'s `<Routes>`), wrapped in `main.tsx` by `<BrowserRouter>` then `<AuthProvider>`.

Backend/frontend integration note: the backend has `CORSMiddleware` configured specifically for this (see the Commands section above) — without it the frontend's requests are silently blocked by the browser regardless of how correct the frontend code is, and that failure mode doesn't show up in `curl` or in the backend's own pytest suite, only in an actual browser.

## Current state

- Auth (all in [main.py](backend/main.py), backed by [auth.py](backend/auth.py)):
  - `POST /auth/register` — creates a `User` (`400` if the email is already registered), returns `UserOut` (never the hash).
  - `POST /auth/login` — form-encoded credentials in, `Token` (access + refresh) out; `401` on bad credentials.
  - `POST /auth/refresh` — refresh token in (JSON body), a fresh `Token` out; `401` if the token is invalid, expired, or not actually a refresh token.
  - `GET /auth/me` — the authenticated user's `UserOut`; added for the frontend's `AuthContext`, see the data-model-conventions note above.
- `Task` and `Event` both have a full CRUD surface, plus `/health`:
  - `POST /tasks` / `POST /events` — create, scoped to `current_user` (`Event` create also rejects `end_time <= start_time` with `422`).
  - `GET /tasks` — list, filtered to `current_user`'s rows, with optional `?status=` / `?priority=` query filters (`Literal`-validated). `GET /events` — list, filtered to `current_user`, ordered by `start_time`, no filters yet.
  - `GET /tasks/{id}` / `GET /events/{id}` — single record, `404` if it doesn't exist or belongs to another user.
  - `PUT /tasks/{id}` / `PUT /events/{id}` — partial update (see `exclude_unset` note above), same `404` rule; the `Event` variant also re-checks `end_time > start_time` after applying the update.
  - `DELETE /tasks/{id}` / `DELETE /events/{id}` — same `404` rule, `204` on success.
  - Every one of these endpoints requires `get_current_user` — there is no unauthenticated access to `Task`/`Event` data anymore.
- `Conversation` has a CRUD surface too, minus update (nothing to edit on one yet): `POST /conversations` (optional `title`), `GET /conversations` (list, newest first), `GET /conversations/{id}` (detail with `messages`, `404` rule same as `Task`/`Event`), `DELETE /conversations/{id}` (`204`/`404`, cascades to its `ChatMessage` rows).
- `POST /conversations/{id}/chat` sends a user message to Groq with the full conversation history as context and returns the assistant's reply — see the data-model-conventions note on `ChatMessage` above for the persistence/error-handling details. No function calling or RAG yet: Groq only ever sees the raw message history, nothing about the user's actual `Task`/`Event` data.
- Four Alembic migrations exist: `0c60286217db_crea_tabla_tasks.py`, `f2dc7a066b05_crea_tabla_events.py`, `2bee24009ca1_crea_tabla_users_y_user_id_en_tasks_.py`, and `5269a23e165c_crea_tablas_conversations_y_chat_.py`.
- A pytest suite (62 tests) covers auth (register/login/refresh/me, token-type confusion, protected-without-token), `Task`/`Event` (listing/filtering, all `404` cases, `422` on invalid filter/update/time-range values, cross-user isolation), `Conversation` (CRUD, ordering, message serialization, cascade delete, cross-user isolation), and chat (history sent to Groq, `502` on a Groq failure, auth/ownership/validation) — the Groq call itself is mocked in tests (see `tests/test_chat.py` above), verified for real only by manual smoke testing.
- Frontend: project setup (Vite + React 19 + TypeScript, `react-router-dom`, `axios`), the `apiClient`/auth-refresh layer, and full authentication (register/login/logout, session restored on page load via `GET /auth/me`, protected routing) all work — see Frontend architecture above. `/` only has the `DashboardPage` placeholder; no task list, calendar, or chat UI yet, and no frontend tests.
- Still no function calling or RAG, no CI, and no frontend tests — all of this is still on the roadmap in the root [README.md](README.md). No password reset, email verification, or refresh-token revocation (logout) yet either.
