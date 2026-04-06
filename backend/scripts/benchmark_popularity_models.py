from __future__ import annotations

import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core import config as _config  # noqa: F401

from app.services.similarity import _build_reference_from_row, _dataset_paths
from app.services.sound_dna import FEATURE_ORDER, vectorize

MODEL_DIR = Path(__file__).resolve().parents[1] / "app" / "data" / "models"
BENCHMARK_PATH = MODEL_DIR / "popularity_benchmark.json"
BEST_MODEL_PATH = MODEL_DIR / "popularity_model.pkl"
BEST_MODEL_META_PATH = MODEL_DIR / "popularity_model_metadata.json"
MODEL_CARD_PATH = MODEL_DIR / "POPULARITY_MODEL_CARD.md"


@dataclass
class DatasetBundle:
    X: np.ndarray
    y: np.ndarray
    artists: np.ndarray
    snapshots: np.ndarray
    rows: int


def _snapshot_rank(path: Path) -> int:
    name = path.stem.lower()
    year_match = re.search(r"(20\d{2})", name)
    year = int(year_match.group(1)) if year_match else 1970

    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    month = 1
    for token, value in month_map.items():
        if token in name:
            month = value
            break

    return (year * 100) + month


def load_dataset() -> DatasetBundle:
    paths = [p for p in _dataset_paths() if p.exists()]
    if not paths:
        raise FileNotFoundError("No Spotify CSV files found. Configure dataset paths in .env.")

    max_rows = int((os.getenv("POPULARITY_MAX_ROWS") or "30000").strip())

    rows_X: list[list[float]] = []
    rows_y: list[float] = []
    artists: list[str] = []
    snapshots: list[int] = []
    seen_track_ids: set[str] = set()

    for path in sorted(paths, key=_snapshot_rank):
        snapshot = _snapshot_rank(path)
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = _build_reference_from_row(row)
                if entry is None:
                    continue

                track_id = str(entry.get("track_id", "") or "")
                if track_id and track_id in seen_track_ids:
                    continue
                if track_id:
                    seen_track_ids.add(track_id)

                artist_name = str(row.get("artist_name") or row.get("artist") or entry.get("artist") or "unknown")
                rows_X.append(vectorize(entry["features"]))
                rows_y.append(float(entry.get("popularity", 0.0)))
                artists.append(artist_name)
                snapshots.append(snapshot)

                if len(rows_X) >= max_rows:
                    break

        if len(rows_X) >= max_rows:
            break

    if not rows_X:
        raise RuntimeError("No usable rows loaded from datasets.")

    X = np.array(rows_X, dtype=np.float32)
    y = np.array(rows_y, dtype=np.float32)
    artist_arr = np.array(artists, dtype=object)
    snapshot_arr = np.array(snapshots, dtype=np.int32)

    return DatasetBundle(X=X, y=y, artists=artist_arr, snapshots=snapshot_arr, rows=len(rows_X))


def build_split(bundle: DatasetBundle) -> tuple[np.ndarray, np.ndarray, str]:
    X = bundle.X
    y = bundle.y
    artists = bundle.artists
    snapshots = bundle.snapshots

    latest_snapshot = int(np.max(snapshots))
    train_mask = snapshots < latest_snapshot
    test_mask = snapshots == latest_snapshot

    if np.any(train_mask) and np.any(test_mask):
        train_artists = set(str(a) for a in artists[train_mask].tolist())
        test_no_leak = np.array([str(a) not in train_artists for a in artists], dtype=bool)
        test_mask = test_mask & test_no_leak

        train_idx = np.where(train_mask)[0]
        test_idx = np.where(test_mask)[0]

        if len(train_idx) >= 5000 and len(test_idx) >= 2000:
            return train_idx, test_idx, "time_plus_artist_holdout"

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=artists))
    return np.array(train_idx), np.array(test_idx), "group_shuffle_fallback"


def evaluate_models(bundle: DatasetBundle, train_idx: np.ndarray, test_idx: np.ndarray) -> list[dict[str, object]]:
    X_train = bundle.X[train_idx]
    y_train = bundle.y[train_idx]
    X_test = bundle.X[test_idx]
    y_test = bundle.y[test_idx]

    n_jobs = int((os.getenv("POPULARITY_N_JOBS") or "1").strip())
    rf_trees = int((os.getenv("POPULARITY_RF_TREES") or "220").strip())
    et_trees = int((os.getenv("POPULARITY_ET_TREES") or "280").strip())
    hgb_iter = int((os.getenv("POPULARITY_HGB_ITER") or "260").strip())

    candidates: dict[str, object] = {
        "mean_baseline": DummyRegressor(strategy="mean"),
        "random_forest": RandomForestRegressor(
            n_estimators=rf_trees,
            max_depth=None,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=n_jobs,
        ),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=et_trees,
            random_state=42,
            n_jobs=n_jobs,
            min_samples_leaf=2,
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            learning_rate=0.05,
            max_depth=8,
            max_iter=hgb_iter,
            random_state=42,
        ),
    }

    results: list[dict[str, object]] = []
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        mae = float(mean_absolute_error(y_test, pred))
        r2 = float(r2_score(y_test, pred))
        results.append(
            {
                "model": name,
                "mae": round(mae, 6),
                "r2": round(r2, 6),
                "train_rows": int(len(train_idx)),
                "test_rows": int(len(test_idx)),
                "estimator": model,
            }
        )

    results.sort(key=lambda row: (float(row["mae"]), -float(row["r2"])))
    return results


def write_model_card(report: dict[str, object]) -> None:
    best = report["best_model"]
    leaderboard = report["leaderboard"]

    lines = [
        "# Popularity Model Card",
        "",
        "## Summary",
        f"- Selected model: {best['model']}",
        f"- MAE: {best['mae']}",
        f"- R2: {best['r2']}",
        f"- Dataset rows: {report['dataset_rows']}",
        f"- Split strategy: {report['split_strategy']}",
        "",
        "## Data & Leakage Controls",
        "- Features: normalized Sound DNA feature vector (14 features)",
        "- Target: Spotify popularity",
        "- Split enforces time-plus-artist holdout when possible, with group-split fallback",
        "",
        "## Leaderboard",
        "| Model | MAE | R2 | Train Rows | Test Rows |",
        "|---|---:|---:|---:|---:|",
    ]

    for row in leaderboard:
        lines.append(
            f"| {row['model']} | {row['mae']} | {row['r2']} | {row['train_rows']} | {row['test_rows']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "- This model is intended for internal ranking/prioritization, not strict causal inference.",
            "- Re-train whenever newer Spotify snapshots are added.",
            "",
        ]
    )

    MODEL_CARD_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    bundle = load_dataset()
    train_idx, test_idx, split_strategy = build_split(bundle)
    results = evaluate_models(bundle, train_idx, test_idx)

    best_row = results[0]
    best_estimator = best_row["estimator"]

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_estimator, BEST_MODEL_PATH)

    leaderboard = [
        {
            "model": str(row["model"]),
            "mae": float(row["mae"]),
            "r2": float(row["r2"]),
            "train_rows": int(row["train_rows"]),
            "test_rows": int(row["test_rows"]),
        }
        for row in results
    ]

    report = {
        "dataset_rows": int(bundle.rows),
        "feature_count": int(bundle.X.shape[1]),
        "split_strategy": split_strategy,
        "models_tested": [str(row["model"]) for row in results],
        "leaderboard": leaderboard,
        "best_model": {
            "model": str(best_row["model"]),
            "mae": float(best_row["mae"]),
            "r2": float(best_row["r2"]),
            "path": str(BEST_MODEL_PATH),
        },
    }

    BENCHMARK_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    BEST_MODEL_META_PATH.write_text(
        json.dumps(
            {
                "model": str(best_row["model"]),
                "mae": float(best_row["mae"]),
                "r2": float(best_row["r2"]),
                "feature_order": FEATURE_ORDER,
                "split_strategy": split_strategy,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_model_card(report)

    print("Popularity benchmark complete")
    print(f"Dataset rows: {bundle.rows}")
    print(f"Split strategy: {split_strategy}")
    print(f"Best model: {best_row['model']}")
    print(f"Best MAE: {best_row['mae']}")
    print(f"Best R2: {best_row['r2']}")
    print(f"Saved benchmark: {BENCHMARK_PATH}")
    print(f"Saved model: {BEST_MODEL_PATH}")
    print(f"Saved model card: {MODEL_CARD_PATH}")


if __name__ == "__main__":
    main()
