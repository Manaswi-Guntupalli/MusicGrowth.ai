from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.similarity import _build_reference_from_row, _dataset_paths
from app.services.sound_dna import vectorize

MODEL_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "models"
REFERENCE_DATASET_PATH = MODEL_DIR / "reference_dataset.json"
MATRIX_PATH = MODEL_DIR / "sound_dna_matrix.npy"
SCALER_PATH = MODEL_DIR / "scaler.pkl"


def build_dataset(min_popularity: float, max_rows: int) -> list[dict]:
    seen_track_ids: set[str] = set()
    refs: list[dict] = []

    for path in _dataset_paths():
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = _build_reference_from_row(row)
                if entry is None:
                    continue

                if float(entry.get("popularity", 0.0)) < min_popularity:
                    continue

                track_id = str(entry.get("track_id", "") or "")
                if track_id and track_id in seen_track_ids:
                    continue

                if track_id:
                    seen_track_ids.add(track_id)
                refs.append(entry)

                if len(refs) >= max_rows:
                    return refs

    return refs


def main() -> None:
    min_popularity = float(os.getenv("SPOTIFY_MIN_POPULARITY", "35"))
    max_rows = int(os.getenv("SPOTIFY_MAX_ROWS", "50000"))

    refs = build_dataset(min_popularity=min_popularity, max_rows=max_rows)
    if len(refs) < 10000:
        raise ValueError(f"Expected at least 10000 references, found {len(refs)}. Check CSV inputs.")

    matrix = np.vstack([np.array(vectorize(r["features"]), dtype=np.float32) for r in refs])
    scaler = StandardScaler()
    scaler.fit(matrix)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with REFERENCE_DATASET_PATH.open("w", encoding="utf-8") as f:
        json.dump(refs, f, indent=2)
    np.save(MATRIX_PATH, matrix)
    joblib.dump(scaler, SCALER_PATH)

    print(f"Reference rows: {len(refs)}")
    print(f"Feature dims: {matrix.shape[1]}")
    print(f"Saved: {REFERENCE_DATASET_PATH}")
    print(f"Saved: {MATRIX_PATH}")
    print(f"Saved: {SCALER_PATH}")


if __name__ == "__main__":
    main()
