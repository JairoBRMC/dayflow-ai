import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no está definida. Copia backend/.env.example a backend/.env y "
        "completa un valor secreto, p. ej.: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl solo es metadata para el botón "Authorize" de /docs; el propio
# /auth/login recibe form-data (OAuth2PasswordRequestForm), no JSON.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="No se pudo validar las credenciales",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(user_id: uuid.UUID, expires_delta: timedelta, token_type: str) -> str:
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str, expected_type: str) -> uuid.UUID:
    """Decodifica y valida un JWT (firma, expiración y tipo). Lanza 401 si algo falla."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise _CREDENTIALS_ERROR

    if payload.get("type") != expected_type:
        raise _CREDENTIALS_ERROR

    raw_user_id = payload.get("sub")
    if raw_user_id is None:
        raise _CREDENTIALS_ERROR

    try:
        return uuid.UUID(raw_user_id)
    except ValueError:
        raise _CREDENTIALS_ERROR


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_token(token, expected_type="access")
    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR
    return user
