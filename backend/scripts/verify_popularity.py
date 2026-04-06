from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.similarity import _build_reference_from_row, _dataset_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify popularity filtering on Spotify reference datasets.")
    parser.add_argument(
        "--min-popularity",
        type=float,
        default=float(os.getenv("SPOTIFY_MIN_POPULARITY", "30")),
        help="Minimum popularity threshold applied to rows",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=int(os.getenv("SPOTIFY_MAX_ROWS", "50000")),
        help="Maximum accepted rows to inspect before stopping",
    )
    return parser.parse_args()


def collect_popularity(min_popularity: float, max_rows: int) -> tuple[list[float], dict[str, int], list[Path]]:
    stats = {
        "rows_scanned": 0,
        "rows_valid": 0,
        "rows_below_threshold": 0,
        "rows_kept": 0,
        "duplicates_skipped": 0,
    }

    values: list[float] = []
    seen_track_ids: set[str] = set()
    paths = _dataset_paths()

    for path in paths:
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["rows_scanned"] += 1
                entry = _build_reference_from_row(row)
                if entry is None:
                    continue

                stats["rows_valid"] += 1
                popularity = float(entry.get("popularity", 0.0))
                if popularity < min_popularity:
                    stats["rows_below_threshold"] += 1
                    continue

                track_id = str(entry.get("track_id", "") or "")
                if track_id and track_id in seen_track_ids:
                    stats["duplicates_skipped"] += 1
                    continue

                if track_id:
                    seen_track_ids.add(track_id)
                values.append(popularity)
                stats["rows_kept"] += 1

                if len(values) >= max_rows:
                    return values, stats, paths

    return values, stats, paths


def main() -> None:
    args = parse_args()
    values, stats, paths = collect_popularity(args.min_popularity, args.max_rows)

    print("dataset_paths", ", ".join(str(path) for path in paths))
    print("rows_scanned", stats["rows_scanned"])
    print("rows_valid", stats["rows_valid"])
    print("rows_below_threshold", stats["rows_below_threshold"])
    print("duplicates_skipped", stats["duplicates_skipped"])
    print("rows_kept", stats["rows_kept"])

    if not values:
        raise SystemExit("No rows passed filtering. Check datasets and --min-popularity setting.")

    min_value = min(values)
    max_value = max(values)
    avg_value = sum(values) / len(values)

    print("popularity_min", round(min_value, 3))
    print("popularity_avg", round(avg_value, 3))
    print("popularity_max", round(max_value, 3))

    if min_value < args.min_popularity:
        raise SystemExit(
            f"Verification failed: kept value {min_value} is below threshold {args.min_popularity}."
        )

    print("verification", "PASS")


if __name__ == "__main__":
    main()
