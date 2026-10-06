import os
from functools import lru_cache

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# A diferencia de DATABASE_URL/SECRET_KEY, GROQ_API_KEY solo hace falta para el
# endpoint de chat -- no para el resto de la API. Por eso no se valida al importar
# este módulo (rompería toda la app, incluido pytest, para quien no tenga clave de
# Groq) sino la primera vez que de verdad se intenta hablar con Groq.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


@lru_cache
def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY no está definida. Copia backend/.env.example a backend/.env "
            "y completa tu clave de Groq (https://console.groq.com/keys)."
        )
    return Groq(api_key=api_key)


def get_chat_completion(messages: list[dict]) -> str:
    """Envía el historial de mensajes (formato OpenAI: [{"role": ..., "content": ...}])
    a Groq y devuelve el contenido de la respuesta del asistente."""
    completion = _get_client().chat.completions.create(model=GROQ_MODEL, messages=messages)
    return completion.choices[0].message.content
