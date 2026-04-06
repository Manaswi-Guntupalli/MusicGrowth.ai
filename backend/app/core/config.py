from __future__ import annotations

import os
from pathlib import Path


def _load_env_file() -> None:
    # Load environment from project root `.env` (or backend/.env) when present.
    candidate_paths = (
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    )

    for env_path in candidate_paths:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if value and value[0] == value[-1] and value[0] in {"\"", "'"}:
                value = value[1:-1]

            os.environ.setdefault(key, value)

        break


_load_env_file()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer.") from exc


MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "musicgrowth")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-demo-placeholder-change-me")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
MAX_UPLOAD_SIZE_BYTES = _env_int("MAX_UPLOAD_SIZE_BYTES", 25 * 1024 * 1024)
UPLOAD_CHUNK_SIZE_BYTES = _env_int("UPLOAD_CHUNK_SIZE_BYTES", 1024 * 1024)

_INSECURE_JWT_SECRET_VALUES = {
    "change-this-in-production",
    "changeme",
    "secret",
    "jwt-secret",
    "replace-with-strong-secret",
}


def validate_startup_environment() -> None:
    errors: list[str] = []

    jwt_secret = (JWT_SECRET_KEY or "").strip()
    if not jwt_secret:
        errors.append("Missing required environment variable JWT_SECRET_KEY.")
    else:
        if jwt_secret.lower() in _INSECURE_JWT_SECRET_VALUES:
            errors.append("JWT_SECRET_KEY uses an insecure placeholder value.")
        if len(jwt_secret) < 32:
            errors.append("JWT_SECRET_KEY must be at least 32 characters long.")

    if MAX_UPLOAD_SIZE_BYTES <= 0:
        errors.append("MAX_UPLOAD_SIZE_BYTES must be greater than 0.")

    if UPLOAD_CHUNK_SIZE_BYTES <= 0:
        errors.append("UPLOAD_CHUNK_SIZE_BYTES must be greater than 0.")

    if UPLOAD_CHUNK_SIZE_BYTES > MAX_UPLOAD_SIZE_BYTES:
        errors.append("UPLOAD_CHUNK_SIZE_BYTES cannot be larger than MAX_UPLOAD_SIZE_BYTES.")

    if errors:
        raise RuntimeError("Invalid environment configuration. " + " ".join(errors))
