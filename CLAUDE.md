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

Tests run against the real dev Postgres from `docker-compose`, not an in-memory/SQLite DB: `models.py` uses `sqlalchemy.dialects.postgresql.UUID`, which isn't portable to SQLite, so hitting the real dev database is simpler than maintaining a second schema. Each test that needs a row creates it via the API and deletes it in fixture teardown (see the `created_task` fixture in [tests/test_tasks.py](backend/tests/test_tasks.py)) rather than relying on shared fixture data, so the dev DB stays clean between runs.

## Architecture

The backend is a flat, single-package FastAPI app (no `app/` src layout, no routers module yet) — everything currently lives directly under `backend/`:

- [database.py](backend/database.py) — loads `DATABASE_URL` from `.env` (raises a clear `RuntimeError` if it's missing), creates the SQLAlchemy `engine`/`SessionLocal`, defines the declarative `Base`, and exposes the `get_db()` dependency used for request-scoped sessions.
- [models.py](backend/models.py) — SQLAlchemy ORM models. Only `Task` exists today.
- [schemas.py](backend/schemas.py) — Pydantic request/response models, kept separate from the ORM models in `models.py`: `TaskCreate` (creation input), `TaskUpdate` (all fields optional, for partial updates), `TaskOut` (response shape, `model_config = ConfigDict(from_attributes=True)` so it can be built straight from a `Task` ORM instance).
- [main.py](backend/main.py) — the FastAPI app and all endpoints (no routers module yet, everything in one file).
- [alembic/env.py](backend/alembic/env.py) — reads `DATABASE_URL` from `.env` itself and points `target_metadata` at `Base.metadata`; every new model must be imported here (next to the `Task` import) or `--autogenerate` won't see it.
- [tests/test_tasks.py](backend/tests/test_tasks.py) — pytest suite for the `Task` CRUD endpoints.

Data model conventions (see [backend/README.md](backend/README.md) for the full planned schema and the ER diagram at `backend/Docs/er-diagram.png`):
- Primary keys are UUIDs (`sqlalchemy.dialects.postgresql.UUID`, `default=uuid.uuid4`), not autoincrement ints.
- Enum-like fields (`status`, `priority`, `role`) are plain `String` columns at the DB level — the allowed values live as a comment next to the column, not a DB/Python enum type. Validation instead happens at the API boundary: `schemas.py` defines `Priority`/`TaskStatus` as `typing.Literal` types and reuses them in both request bodies and query params, so an invalid value (`priority=urgentisimo`) is rejected with FastAPI's automatic `422` before it ever reaches the DB.
- `created_at` uses `server_default=func.now()` rather than an application-side default.
- Endpoints that take a resource id look it up with a shared `_get_task_or_404` helper ([main.py](backend/main.py)) rather than repeating the `None` check, and raise `HTTPException(status_code=404)` — followed for `GET`/`PUT`/`DELETE` `/tasks/{id}`.
- `PUT /tasks/{id}` is a partial update in practice: `TaskUpdate` fields all default to `None`, and the handler applies `task_update.model_dump(exclude_unset=True)` so only fields actually present in the request body overwrite the row — a field omitted from the JSON body is left untouched rather than being reset to `None`.

Planned entities beyond `Task` (not yet implemented): `User`, `Event`, `ChatMessage`, and a future `Goal` to group tasks — see [backend/README.md](backend/README.md) for fields and relationships (all are 1:N off of `User`).

## Current state

- `Task` has a full CRUD surface plus `/health`, all in [main.py](backend/main.py):
  - `POST /tasks` — create.
  - `GET /tasks` — list, with optional `?status=` / `?priority=` query filters (`Literal`-validated).
  - `GET /tasks/{id}` — single task, `404` if it doesn't exist.
  - `PUT /tasks/{id}` — partial update (see `exclude_unset` note above), `404` if it doesn't exist.
  - `DELETE /tasks/{id}` — `404` if it doesn't exist, `204` on success.
  - None of this has auth or a user association yet — the `Task` model still has no `user_id` FK, despite the planned schema calling for one, so `GET /tasks` currently returns every task in the table.
- One Alembic migration exists (`0c60286217db_crea_tabla_tasks.py`), creating the `tasks` table.
- A pytest suite covers the `Task` endpoints (listing/filtering, all three `404` cases, and `422` on invalid filter/update values), but it isn't wired into any CI yet.
- No authentication, no `User` model, no `Event`/`ChatMessage` models, no AI/chat integration, no frontend, and no CI yet — all of this is still on the roadmap in the root [README.md](README.md).
