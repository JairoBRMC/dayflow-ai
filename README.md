# Dayflow AI

Asistente inteligente para organizar tareas y objetivos personales, con un chat de IA que ayuda a planificar el día.

## Estado del proyecto
🚧 En desarrollo activo — backend con auth, tareas, eventos y chat con IA funcionando; frontend con el login/registro ya conectado al backend, falta la interfaz real de tareas/calendario/chat (ver [Roadmap](#roadmap)).

## Stack
- **Frontend:** React 19 + TypeScript, Vite, `react-router-dom`, `axios`
- **Backend:** Python 3.12 + FastAPI
- **Base de datos:** PostgreSQL (una instancia para desarrollo y otra, aparte, para tests)
- **Auth:** JWT (access + refresh) con PyJWT, contraseñas con passlib/bcrypt
- **Validación:** Pydantic v2
- **Migraciones:** Alembic
- **Tests:** pytest + `TestClient` de FastAPI
- **IA:** Groq para el chat — function calling y RAG sobre las tareas/eventos reales del usuario, planeados, todavía no implementados
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
# Y añade tu GROQ_API_KEY (https://console.groq.com/keys) -- solo hace falta
# para el chat (POST /conversations/{id}/chat), el resto de la API funciona sin ella.
# Si el frontend corre en otra URL que no sea localhost:5173, ajusta CORS_ORIGINS.

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

## Instalación (frontend)

Con el backend ya arriba (paso anterior):

```bash
cd frontend
npm install
cp .env.example .env   # por defecto ya apunta a http://127.0.0.1:8000
npm run dev
```

La app queda en `http://localhost:5173` (o el puerto que Vite elija si ese está ocupado — lo imprime al arrancar; si cambia, añádelo a `CORS_ORIGINS` en el `.env` del backend).

## Roadmap
- [x] Backend base: CRUD de `Task` y `Event`, autenticación JWT (registro/login/refresh), endpoints protegidos y filtrados por usuario
- [ ] Frontend: setup del proyecto, capa de API con refresh automático, y autenticación (login/registro/sesión persistida) ya funcionan; falta la interfaz de tareas, calendario y chat
- [ ] Chat con IA para planificación diaria — `Conversation`/`ChatMessage` y `POST /conversations/{id}/chat` (Groq, con historial) ya funcionan; falta function calling y RAG sobre las tareas/eventos reales
- [ ] Estadísticas
- [x] Tests (pytest, base de datos de test dedicada) — falta CI/CD y tests de frontend
- [ ] Despliegue
