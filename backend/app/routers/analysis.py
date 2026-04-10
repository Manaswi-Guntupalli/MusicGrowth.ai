from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError
import librosa
import soundfile as sf

from ..core.config import MAX_UPLOAD_SIZE_BYTES, UPLOAD_CHUNK_SIZE_BYTES
from ..db.mongodb import get_db
from ..dependencies.auth import get_current_user
from ..models.schemas import (
    AnalysisHistoryItem,
    AnalysisResponse,
    CreativePathAISummaryRequest,
    CreativePathAISummaryResponse,
    TrajectoryOptimizationRequest,
    TrajectoryOptimizationResponse,
    TrajectorySimulationRequest,
    TrajectorySimulationResponse,
)
from ..services.explainability import build_creative_paths_ai_summary
from ..services.pipeline import run_analysis
from ..services.trajectory import run_auto_optimize, run_trajectory_simulation

router = APIRouter(tags=["analysis"])
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}


def _max_upload_size_mb() -> int:
    return max(1, int(MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)))


async def _write_upload_to_temp_file(file: UploadFile, suffix: str) -> tuple[str, int]:
    tmp_path: str | None = None
    total_size = 0

    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name

            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE_BYTES)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum upload size is {_max_upload_size_mb()} MB.",
                    )

                tmp.write(chunk)
    except Exception:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise

    if total_size <= 0:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if tmp_path is None:
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")

    return tmp_path, total_size


def _validate_uploaded_audio_file(audio_path: str) -> None:
    try:
        info = sf.info(audio_path)
        if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio appears empty or corrupted.",
            )
        return
    except HTTPException:
        raise
    except Exception:
        # Some valid formats (especially mp3 on Windows) may not be readable by
        # libsndfile. Fall back to librosa decoder for compatibility.
        try:
            y, sr = librosa.load(audio_path, sr=22050, mono=True, duration=5.0)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio could not be parsed. The file may be corrupted or unsupported.",
            ) from exc

        if y is None or len(y) == 0 or sr <= 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded audio appears empty or corrupted.",
            )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_song(
    file: UploadFile = File(...),
    segment_mode: str = "best",
    allow_spoken_word: bool = False,
    current_user: dict = Depends(get_current_user),
) -> AnalysisResponse:
    extension = Path(file.filename or "upload").suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    if segment_mode not in {"best", "full"}:
        raise HTTPException(status_code=400, detail="segment_mode must be 'best' or 'full'.")

    suffix = extension if extension else ".wav"
    tmp_path: str | None = None

    try:
        tmp_path, _ = await _write_upload_to_temp_file(file=file, suffix=suffix)
        _validate_uploaded_audio_file(tmp_path)

        result = run_analysis(
            tmp_path,
            segment_mode=segment_mode,
            allow_spoken_word=allow_spoken_word,
        )
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
    except HTTPException:
        raise
    except ValueError as exc:
        detail = str(exc).strip() or "Unable to analyze this audio file. Please upload a valid, non-corrupted music track."
        logger.warning(
            "Audio analysis validation failed for file=%s user=%s detail=%s",
            file.filename,
            current_user.get("id"),
            detail,
        )
        raise HTTPException(
            status_code=400,
            detail=detail,
        ) from exc
    except Exception as exc:  # pragma: no cover - safe API guard
        logger.exception("Audio analysis failed unexpectedly for file=%s user=%s", file.filename, current_user.get("id"))
        raise HTTPException(
            status_code=500,
            detail="Analysis failed due to an internal error. Please try again.",
        ) from exc
    finally:
        await file.close()
        try:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)
        except OSError:
            pass


@router.get("/analyses", response_model=list[AnalysisHistoryItem])
async def list_analyses(current_user: dict = Depends(get_current_user)) -> list[AnalysisHistoryItem]:
    db = get_db()
    cursor = db.song_analyses.find({"user_id": ObjectId(current_user["id"])}).sort("created_at", -1)

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


@router.post("/simulate-trajectory", response_model=TrajectorySimulationResponse)
async def simulate_trajectory(
    payload: TrajectorySimulationRequest,
    current_user: dict = Depends(get_current_user),
) -> TrajectorySimulationResponse:
    _ = current_user  # Keep endpoint auth-protected for user-level usage telemetry.

    try:
        simulated = run_trajectory_simulation(payload.base_features, payload.adjustments)
        return TrajectorySimulationResponse(**simulated)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safe API guard
        logger.exception("Trajectory simulation failed unexpectedly for user=%s", current_user.get("id"))
        raise HTTPException(
            status_code=500,
            detail="Trajectory simulation failed due to an internal error. Please try again.",
        ) from exc


@router.post("/creative-paths-ai-summary", response_model=CreativePathAISummaryResponse)
async def creative_paths_ai_summary(
    payload: CreativePathAISummaryRequest,
    current_user: dict = Depends(get_current_user),
) -> CreativePathAISummaryResponse:
    _ = current_user

    try:
        summarized = build_creative_paths_ai_summary(payload.model_dump())
        return CreativePathAISummaryResponse(**summarized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safe API guard
        logger.exception("Creative paths AI summary failed unexpectedly for user=%s", current_user.get("id"))
        raise HTTPException(
            status_code=500,
            detail="Creative paths AI summary failed due to an internal error. Please try again.",
        ) from exc


@router.post("/optimize-trajectory", response_model=TrajectoryOptimizationResponse)
async def optimize_trajectory(
    payload: TrajectoryOptimizationRequest,
    current_user: dict = Depends(get_current_user),
) -> TrajectoryOptimizationResponse:
    _ = current_user

    try:
        optimized = run_auto_optimize(
            base_features=payload.base_features,
            objective=payload.objective,
            adjustable_features=payload.adjustable_features,
        )
        return TrajectoryOptimizationResponse(**optimized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safe API guard
        logger.exception("Trajectory optimization failed unexpectedly for user=%s", current_user.get("id"))
        raise HTTPException(
            status_code=500,
            detail="Trajectory optimization failed due to an internal error. Please try again.",
        ) from exc
