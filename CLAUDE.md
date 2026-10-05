# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Dayflow AI is a personal task/goal planning assistant with an AI chat that helps plan the user's day (function calling + RAG over the user's tasks/events, planned). The project is in early, active development — only the backend skeleton exists so far.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL 16 (via Docker), accessed with SQLAlchemy 2.x
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Auth:** JWT (access + refresh) via PyJWT, password hashing via passlib (`CryptContext(schemes=["bcrypt"])`)
- **Frontend:** React + TypeScript (not started — `frontend/` is currently empty)
- **AI:** OpenAI API — function calling + RAG (not implemented yet)
- **Testing:** pytest + FastAPI's `TestClient`
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

There is no lint or CI setup yet — those commands don't exist in this repo currently.

`.env` needs a `SECRET_KEY` (JWT signing secret) alongside `DATABASE_URL` and `TEST_DATABASE_URL` — generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. Like `DATABASE_URL`, `database.py`/`auth.py` raise a `RuntimeError` on startup if it's missing rather than failing later with a confusing error; `tests/conftest.py` does the same for `TEST_DATABASE_URL`.

`requirements.txt` pins `bcrypt==4.0.1`: passlib 1.7.4 (unmaintained) reads `bcrypt.__about__.__version__` to detect the backend, which `bcrypt>=4.1` removed, so anything newer breaks `CryptContext(schemes=["bcrypt"])` at the first `.hash()`/`.verify()` call. Don't bump `bcrypt` past `4.0.x` without also moving off passlib.

**Tests run against their own Postgres, never the dev database.** `docker-compose.yml` defines a second service, `db_test` (port `5434`, db `dayflow_test_db`), and `tests/conftest.py` points at it via `TEST_DATABASE_URL`, not `DATABASE_URL`. A session-scoped autouse fixture in `conftest.py` runs `alembic upgrade head` against `TEST_DATABASE_URL` before the first test (temporarily reassigning the `DATABASE_URL` env var just for that one call, since `alembic/env.py` reads it directly — the dev DB is never touched), so the test DB goes from empty to the full schema automatically; there's no manual migration step before running `pytest`. `main.py`'s `get_db` dependency is overridden (`app.dependency_overrides[get_db]`) to hand out sessions bound to the test engine instead, so the app code under test is unmodified. Cleanup between tests is still explicit create-via-API-then-delete-in-teardown (see the fixtures in `tests/conftest.py`), not transaction-per-test-with-rollback: the suite's actual cost is bcrypt hashing (~100ms+ per register/login), not database I/O, so a transactional-rollback harness would add real complexity (wrapping `get_db()` in nested `SAVEPOINT`s so the app's own `db.commit()` calls don't break the rollback) for a speedup that wouldn't show up anywhere. Revisit that trade-off if the suite grows enough that DB cleanup, not hashing, becomes the bottleneck.

## Architecture

The backend is a flat, single-package FastAPI app (no `app/` src layout, no routers module yet) — everything currently lives directly under `backend/`:

- [database.py](backend/database.py) — loads `DATABASE_URL` from `.env` (raises a clear `RuntimeError` if it's missing), creates the SQLAlchemy `engine`/`SessionLocal`, defines the declarative `Base`, and exposes the `get_db()` dependency used for request-scoped sessions.
- [models.py](backend/models.py) — SQLAlchemy ORM models: `User`, `Task`, `Event`, `Conversation`, `ChatMessage`.
- [schemas.py](backend/schemas.py) — Pydantic request/response models, kept separate from the ORM models in `models.py`: a `*Create`/`*Update`/`*Out` trio per entity (`TaskCreate`/`TaskUpdate`/`TaskOut`, `EventCreate`/`EventUpdate`/`EventOut`), plus `UserCreate`/`UserOut`, `Token`, `RefreshRequest` for auth, and `ConversationCreate`/`ConversationOut`/`ConversationDetail`/`MessageOut` for chat. `*Out` schemas use `model_config = ConfigDict(from_attributes=True)` so they can be built straight from the ORM instance; `*Update` schemas have every field optional, for partial updates.
- [auth.py](backend/auth.py) — password hashing (`hash_password`/`verify_password` via passlib), JWT creation/decoding (`create_access_token`, `create_refresh_token`, `decode_token`), and the `get_current_user` dependency that every protected endpoint depends on. Reads `SECRET_KEY` from `.env` the same way `database.py` reads `DATABASE_URL` (`RuntimeError` if missing).
- [main.py](backend/main.py) — the FastAPI app and all endpoints (no routers module yet, everything in one file).
- [alembic/env.py](backend/alembic/env.py) — reads `DATABASE_URL` from `.env` itself and points `target_metadata` at `Base.metadata`; every new model must be imported here (next to the existing imports) or `--autogenerate` won't see it.
- [tests/conftest.py](backend/tests/conftest.py) — points the app at the dedicated test database and migrates it (see Commands above), then defines shared fixtures: `auth_headers`/`registered_email` (one test user, via `registered_user`) and `other_user_headers` (a second, independent user, for cross-user isolation tests). Both clean up their user in teardown; `ondelete="CASCADE"` on `Task.user_id`/`Event.user_id`/`Conversation.user_id`/`ChatMessage.conversation_id` takes their rows with them.
- [tests/test_tasks.py](backend/tests/test_tasks.py), [tests/test_events.py](backend/tests/test_events.py), [tests/test_auth.py](backend/tests/test_auth.py), [tests/test_conversations.py](backend/tests/test_conversations.py) — pytest suites, one file per entity/concern.

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
- `ChatMessage` has no `user_id` of its own — ownership is inherited through `ChatMessage.conversation_id → Conversation.user_id`, since a message only ever makes sense as part of one user's conversation. `Conversation.user_id` is `NOT NULL` (unlike `Task`/`Event`'s `user_id`): it's a brand-new table with no pre-auth rows to accommodate, so there was no reason to make it nullable.
- `GET /conversations` (list) returns `ConversationOut` — no messages — while `GET /conversations/{id}` (detail) returns `ConversationDetail`, which adds a `messages: list[MessageOut]` field populated by a second, explicit query (`ChatMessage` filtered by `conversation_id`, ordered by `created_at`). Deliberately not a SQLAlchemy `relationship()`/eager-load: listing conversations would otherwise pull every message of every conversation just to discard them, and the codebase doesn't use ORM relationships anywhere else either (every other query is explicit, e.g. `_get_owned_or_404`, the `Task`/`Event` list filters).
- There's no `POST /conversations/{id}/messages` endpoint yet — `ChatMessage` rows aren't created through the API at all until the AI integration lands (see TO-DO Bloque 4.3+). Until then, `tests/test_conversations.py` inserts `ChatMessage` rows directly via `TestSessionLocal` to exercise `GET /conversations/{id}`'s message serialization.

Planned beyond `User`/`Task`/`Event`/`Conversation`/`ChatMessage`: the AI chat integration itself (an endpoint that calls an LLM, saves the exchange as `ChatMessage` rows, does function calling against `Task`/`Event`, and does basic RAG over the user's own data), plus a future `Goal` entity to group tasks — see [backend/README.md](backend/README.md) and the root [TO-DO.txt](TO-DO.txt) for the full breakdown.

## Current state

- Auth (all in [main.py](backend/main.py), backed by [auth.py](backend/auth.py)):
  - `POST /auth/register` — creates a `User` (`400` if the email is already registered), returns `UserOut` (never the hash).
  - `POST /auth/login` — form-encoded credentials in, `Token` (access + refresh) out; `401` on bad credentials.
  - `POST /auth/refresh` — refresh token in (JSON body), a fresh `Token` out; `401` if the token is invalid, expired, or not actually a refresh token.
- `Task` and `Event` both have a full CRUD surface, plus `/health`:
  - `POST /tasks` / `POST /events` — create, scoped to `current_user` (`Event` create also rejects `end_time <= start_time` with `422`).
  - `GET /tasks` — list, filtered to `current_user`'s rows, with optional `?status=` / `?priority=` query filters (`Literal`-validated). `GET /events` — list, filtered to `current_user`, ordered by `start_time`, no filters yet.
  - `GET /tasks/{id}` / `GET /events/{id}` — single record, `404` if it doesn't exist or belongs to another user.
  - `PUT /tasks/{id}` / `PUT /events/{id}` — partial update (see `exclude_unset` note above), same `404` rule; the `Event` variant also re-checks `end_time > start_time` after applying the update.
  - `DELETE /tasks/{id}` / `DELETE /events/{id}` — same `404` rule, `204` on success.
  - Every one of these endpoints requires `get_current_user` — there is no unauthenticated access to `Task`/`Event` data anymore.
- `Conversation` has a CRUD surface too, minus update (nothing to edit on one yet): `POST /conversations` (optional `title`), `GET /conversations` (list, newest first), `GET /conversations/{id}` (detail with `messages`, `404` rule same as `Task`/`Event`), `DELETE /conversations/{id}` (`204`/`404`, cascades to its `ChatMessage` rows). No message-sending endpoint yet — see the data-model-conventions note on `ChatMessage` above.
- Four Alembic migrations exist: `0c60286217db_crea_tabla_tasks.py`, `f2dc7a066b05_crea_tabla_events.py`, `2bee24009ca1_crea_tabla_users_y_user_id_en_tasks_.py`, and `5269a23e165c_crea_tablas_conversations_y_chat_.py`.
- A pytest suite (53 tests) covers auth (register/login/refresh, token-type confusion, protected-without-token), `Task`/`Event` (listing/filtering, all `404` cases, `422` on invalid filter/update/time-range values, cross-user isolation), and `Conversation` (CRUD, ordering, message serialization, cascade delete, cross-user isolation).
- Still no AI/chat integration (no LLM calls, no function calling, no RAG), no frontend, and no CI — all of this is still on the roadmap in the root [README.md](README.md). No password reset, email verification, or refresh-token revocation (logout) yet either.
