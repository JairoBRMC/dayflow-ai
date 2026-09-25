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
```

There is no lint, test, or CI setup yet — none of these commands exist in this repo currently.

## Architecture

The backend is a flat, single-package FastAPI app (no `app/` src layout, no routers module yet) — everything currently lives directly under `backend/`:

- [database.py](backend/database.py) — loads `DATABASE_URL` from `.env`, creates the SQLAlchemy `engine`/`SessionLocal`, defines the declarative `Base`, and exposes the `get_db()` dependency used for request-scoped sessions.
- [models.py](backend/models.py) — SQLAlchemy ORM models. Only `Task` exists today.
- [main.py](backend/main.py) — the FastAPI app, endpoints, and (currently) Pydantic request schemas defined inline in the same file rather than a separate schemas module.
- [alembic/env.py](backend/alembic/env.py) — reads `DATABASE_URL` from `.env` itself and points `target_metadata` at `Base.metadata`; every new model must be imported here (next to the `Task` import) or `--autogenerate` won't see it.

Data model conventions (see [backend/README.md](backend/README.md) for the full planned schema and the ER diagram at `backend/Docs/er-diagram.png`):
- Primary keys are UUIDs (`sqlalchemy.dialects.postgresql.UUID`, `default=uuid.uuid4`), not autoincrement ints.
- Enum-like fields (`status`, `priority`, `role`) are plain `String` columns with the allowed values documented in a comment, not a DB/Python enum type.
- `created_at` uses `server_default=func.now()` rather than an application-side default.

Planned entities beyond `Task` (not yet implemented): `User`, `Event`, `ChatMessage`, and a future `Goal` to group tasks — see [backend/README.md](backend/README.md) for fields and relationships (all are 1:N off of `User`).

## Current state

- Only one endpoint beyond `/health` exists: `POST /tasks`, which creates a `Task` directly from a `TaskCreate` Pydantic model with no auth and no user association yet (the `Task` model has no `user_id` FK yet, despite the planned schema calling for one).
- One Alembic migration exists (`0c60286217db_crea_tabla_tasks.py`), creating the `tasks` table.
- No authentication, no `User` model, no `Event`/`ChatMessage` models, no AI/chat integration, no frontend, and no tests/CI yet — all of this is still on the roadmap in the root [README.md](README.md).
