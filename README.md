# Dayflow AI

Asistente inteligente para organizar tareas y objetivos personales, con un chat de IA que ayuda a planificar el día.

## Estado del proyecto
🚧 En desarrollo activo — backend con auth, tareas y eventos funcionando; chat con IA, estadísticas y frontend todavía por hacer (ver [Roadmap](#roadmap)).

## Stack
- **Frontend:** React + TypeScript (todavía no iniciado)
- **Backend:** Python 3.12 + FastAPI
- **Base de datos:** PostgreSQL (una instancia para desarrollo y otra, aparte, para tests)
- **Auth:** JWT (access + refresh) con PyJWT, contraseñas con passlib/bcrypt
- **Validación:** Pydantic v2
- **Migraciones:** Alembic
- **Tests:** pytest + `TestClient` de FastAPI
- **IA:** OpenAI API (function calling + RAG) — planeado, todavía no implementado
- **Infraestructura:** Docker, GitHub Actions (planeado)

Más detalle del modelo de datos y los endpoints en [backend/README.md](backend/README.md).

## Instalación (backend)

Requiere Python 3.12, Docker y Docker Compose.

```bash
# 1. Levanta las dos bases de datos de Postgres (desarrollo y tests)
docker-compose up -d

# 2. Entorno virtual e instalación de dependencias
cd backend
python -m venv venv
venv\Scripts\activate          # en Windows; en Linux/Mac: source venv/bin/activate
pip install -r requirements.txt

# 3. Variables de entorno
cp .env.example .env
# Edita .env y genera un SECRET_KEY propio:
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Aplica las migraciones a la base de desarrollo
alembic upgrade head

# 5. Arranca la API
uvicorn main:app --reload
```

La API queda en `http://localhost:8000`, con documentación interactiva en `http://localhost:8000/docs`.

### Tests

```bash
cd backend
pytest
```

Los tests corren contra su propia base de datos (el servicio `db_test` de `docker-compose.yml`, ya levantado en el paso 1), nunca contra la de desarrollo. Las migraciones de esa base de test se aplican automáticamente al arrancar la suite — no hace falta ningún paso manual aparte de tener `db_test` arriba.

## Roadmap
- [x] Backend base: CRUD de `Task` y `Event`, autenticación JWT (registro/login/refresh), endpoints protegidos y filtrados por usuario
- [ ] Frontend base
- [ ] Chat con IA para planificación diaria (function calling + RAG)
- [ ] Estadísticas
- [x] Tests (pytest, base de datos de test dedicada) — falta CI/CD
- [ ] Despliegue
