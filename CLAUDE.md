# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Dayflow AI is a personal task/goal planning assistant with an AI chat that helps plan the user's day (function calling + RAG over the user's tasks/events, planned). The project is in early, active development — only the backend skeleton exists so far.

## Stack

- **Backend:** Python 3.12 + FastAPI
- **Database:** PostgreSQL 16 (via Docker), accessed with SQLAlchemy 2.x
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Frontend:** React + TypeScript (not started — `frontend/` is currently empty)
- **AI:** OpenAI API — function calling + RAG (not implemented yet)
- **Testing:** pytest + FastAPI's `TestClient`
- **Infra:** Docker (Postgres today; GitHub Actions planned)

## Commands

All backend commands run from `backend/` with the virtualenv (`backend/venv`) activated.

```
# Start Postgres (from repo root)
docker-compose up -d

# Run the API with reload
uvicorn main:app --reload

# Create a new migration from model changes
alembic revision --autogenerate -m "descripcion en español"

# Apply migrations
alembic upgrade head

# Run the test suite (requires Postgres up and migrations applied — see below)
pytest

# Run a single test
pytest tests/test_tasks.py::test_get_task_not_found_returns_404
```

There is no lint or CI setup yet — those commands don't exist in this repo currently.

Tests run against the real dev Postgres from `docker-compose`, not an in-memory/SQLite DB: `models.py` uses `sqlalchemy.dialects.postgresql.UUID`, which isn't portable to SQLite, so hitting the real dev database is simpler than maintaining a second schema. Each test that needs a row creates it via the API and deletes it in fixture teardown (see the `created_task`/`created_event` fixtures in `tests/`) rather than relying on shared fixture data, so the dev DB stays clean between runs.

## Architecture

The backend is a flat, single-package FastAPI app (no `app/` src layout, no routers module yet) — everything currently lives directly under `backend/`:

- [database.py](backend/database.py) — loads `DATABASE_URL` from `.env` (raises a clear `RuntimeError` if it's missing), creates the SQLAlchemy `engine`/`SessionLocal`, defines the declarative `Base`, and exposes the `get_db()` dependency used for request-scoped sessions.
- [models.py](backend/models.py) — SQLAlchemy ORM models: `Task` and `Event` today.
- [schemas.py](backend/schemas.py) — Pydantic request/response models, kept separate from the ORM models in `models.py`: a `*Create`/`*Update`/`*Out` trio per entity (`TaskCreate`/`TaskUpdate`/`TaskOut`, `EventCreate`/`EventUpdate`/`EventOut`). `*Out` schemas use `model_config = ConfigDict(from_attributes=True)` so they can be built straight from the ORM instance; `*Update` schemas have every field optional, for partial updates.
- [main.py](backend/main.py) — the FastAPI app and all endpoints (no routers module yet, everything in one file).
- [alembic/env.py](backend/alembic/env.py) — reads `DATABASE_URL` from `.env` itself and points `target_metadata` at `Base.metadata`; every new model must be imported here (next to the existing `Task`/`Event` imports) or `--autogenerate` won't see it.
- [tests/test_tasks.py](backend/tests/test_tasks.py), [tests/test_events.py](backend/tests/test_events.py) — pytest suites for the `Task` and `Event` CRUD endpoints, one file per entity.

Data model conventions (see [backend/README.md](backend/README.md) for the full planned schema and the ER diagram at `backend/Docs/er-diagram.png`):
- Primary keys are UUIDs (`sqlalchemy.dialects.postgresql.UUID`, `default=uuid.uuid4`), not autoincrement ints.
- Enum-like fields (`status`, `priority`, `role`) are plain `String` columns at the DB level — the allowed values live as a comment next to the column, not a DB/Python enum type. Validation instead happens at the API boundary: `schemas.py` defines `Priority`/`TaskStatus` as `typing.Literal` types and reuses them in both request bodies and query params, so an invalid value (`priority=urgentisimo`) is rejected with FastAPI's automatic `422` before it ever reaches the DB.
- `created_at` uses `server_default=func.now()` rather than an application-side default.
- Endpoints that take a resource id look it up with a shared `_get_or_404(model, obj_id, db)` helper ([main.py](backend/main.py)) generic over the ORM model, rather than repeating the `None` check per entity, and raise `HTTPException(status_code=404, detail=f"{model.__name__} not found")` — used by `GET`/`PUT`/`DELETE` on both `/tasks/{id}` and `/events/{id}`.
- `PUT` endpoints are partial updates in practice: `*Update` schema fields all default to `None`, and the handler applies `update.model_dump(exclude_unset=True)` so only fields actually present in the request body overwrite the row — a field omitted from the JSON body is left untouched rather than being reset to `None`.
- `Event` additionally validates `end_time > start_time`: on create, a Pydantic `model_validator(mode="after")` on `EventCreate` rejects an invalid range with `422` before a row is ever built; on update, since `EventUpdate` allows changing just one of the two timestamps, the check instead happens in the `PUT /events/{id}` handler itself, after merging the update into the loaded `Event`, so it catches a bad combination no matter which field changed.

Planned entities beyond `Task`/`Event` (not yet implemented): `User`, `ChatMessage`, and a future `Goal` to group tasks — see [backend/README.md](backend/README.md) for fields and relationships (all are 1:N off of `User`).

## Current state

- `Task` and `Event` both have a full CRUD surface, plus `/health`, all in [main.py](backend/main.py):
  - `POST /tasks` / `POST /events` — create (`Event` create rejects `end_time <= start_time` with `422`).
  - `GET /tasks` — list, with optional `?status=` / `?priority=` query filters (`Literal`-validated). `GET /events` — list, ordered by `start_time`, no filters yet.
  - `GET /tasks/{id}` / `GET /events/{id}` — single record, `404` if it doesn't exist.
  - `PUT /tasks/{id}` / `PUT /events/{id}` — partial update (see `exclude_unset` note above), `404` if it doesn't exist; the `Event` variant also re-checks `end_time > start_time` after applying the update.
  - `DELETE /tasks/{id}` / `DELETE /events/{id}` — `404` if it doesn't exist, `204` on success.
  - None of this has auth or a user association yet — neither model has a `user_id` FK, despite the planned schema calling for one, so the list endpoints currently return every row in the table.
- Two Alembic migrations exist: `0c60286217db_crea_tabla_tasks.py` and `f2dc7a066b05_crea_tabla_events.py`.
- A pytest suite (23 tests) covers both entities' endpoints (listing/filtering, all `404` cases, and `422` on invalid filter/update/time-range values), but it isn't wired into any CI yet.
- No authentication, no `User` model, no `ChatMessage` model, no AI/chat integration, no frontend, and no CI yet — all of this is still on the roadmap in the root [README.md](README.md).
