from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError

from ..db.mongodb import get_db
from ..dependencies.auth import get_current_user
from ..models.schemas import AnalysisHistoryItem, AnalysisResponse
from ..services.pipeline import run_analysis

router = APIRouter(tags=["analysis"])

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_song(
    file: UploadFile = File(...),
    segment_mode: str = "best",
    current_user: dict = Depends(get_current_user),
) -> AnalysisResponse:
    extension = Path(file.filename or "upload").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    if segment_mode not in {"best", "full"}:
        raise HTTPException(status_code=400, detail="segment_mode must be 'best' or 'full'.")

    suffix = extension if extension else ".wav"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        content = await file.read()
        tmp.write(content)

    try:
        result = run_analysis(tmp_path, segment_mode=segment_mode)
        db = get_db()
        doc = {
            "user_id": ObjectId(current_user["id"]),
            "filename": file.filename or "upload",
            "segment_mode": segment_mode,
            "result": result,
            "created_at": datetime.now(UTC),
        }
        inserted = await db.song_analyses.insert_one(doc)
        result["analysis_id"] = str(inserted.inserted_id)
        return AnalysisResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safe API guard
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


@router.get("/analyses", response_model=list[AnalysisHistoryItem])
async def list_analyses(current_user: dict = Depends(get_current_user)) -> list[AnalysisHistoryItem]:
    db = get_db()
    cursor = db.song_analyses.find({"user_id": ObjectId(current_user["id"])}).sort("created_at", -1).limit(20)

    items: list[AnalysisHistoryItem] = []
    async for doc in cursor:
        sound_dna = doc.get("result", {}).get("sound_dna", {})
        parsed_result: AnalysisResponse | None = None
        if doc.get("result"):
            try:
                parsed_result = AnalysisResponse(**doc["result"])
            except ValidationError:
                # Keep legacy/malformed records in history without breaking the whole endpoint.
                parsed_result = None

        items.append(
            AnalysisHistoryItem(
                id=str(doc["_id"]),
                filename=doc.get("filename", "upload"),
                segment_mode=doc.get("segment_mode", "best"),
                mood=sound_dna.get("mood", "Unknown"),
                production_style=sound_dna.get("production_style", "Unknown"),
                created_at=doc.get("created_at", datetime.now(UTC)),
                result=parsed_result,
            )
        )
    return items
