from __future__ import annotations

import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "musicgrowth")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-demo-placeholder-change-me")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
