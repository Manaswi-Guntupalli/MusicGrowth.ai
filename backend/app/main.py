from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import validate_startup_environment
from .db.mongodb import init_indexes
from .routers.analysis import router as analysis_router
from .routers.auth import router as auth_router

app = FastAPI(title="MusicGrowth.AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup() -> None:
    validate_startup_environment()
    await init_indexes()


app.include_router(analysis_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
