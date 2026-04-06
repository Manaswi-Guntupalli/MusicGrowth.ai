from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any
from urllib.request import urlopen

SOURCE_URL_DEFAULT = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "master/data/2020/2020-01-21/spotify_songs.csv"
)

OUTPUT_HEADERS = [
    "artist_name",
    "track_name",
    "track_id",
    "popularity",
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
]


def _first_non_empty(row: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _safe_float_text(value: str, fallback: float = 0.0) -> str:
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return str(fallback)


def _normalize_row(raw: dict[str, Any]) -> dict[str, str] | None:
    track_name = _first_non_empty(raw, ["track_name", "song"], default="Unknown Track")
    artist_name = _first_non_empty(raw, ["artist_name", "track_artist", "artist"], default="Unknown Artist")
    track_id = _first_non_empty(raw, ["track_id", "id"], default="")

    popularity_text = _first_non_empty(raw, ["popularity", "track_popularity"], default="0")
    popularity = _safe_float_text(popularity_text, fallback=0.0)

    normalized = {
        "artist_name": artist_name,
        "track_name": track_name,
        "track_id": track_id,
        "popularity": popularity,
        "danceability": _safe_float_text(_first_non_empty(raw, ["danceability"], default="0"), fallback=0.0),
        "energy": _safe_float_text(_first_non_empty(raw, ["energy"], default="0"), fallback=0.0),
        "key": _safe_float_text(_first_non_empty(raw, ["key"], default="0"), fallback=0.0),
        "loudness": _safe_float_text(_first_non_empty(raw, ["loudness"], default="-15"), fallback=-15.0),
        "mode": _safe_float_text(_first_non_empty(raw, ["mode"], default="0"), fallback=0.0),
        "speechiness": _safe_float_text(_first_non_empty(raw, ["speechiness"], default="0"), fallback=0.0),
        "acousticness": _safe_float_text(_first_non_empty(raw, ["acousticness"], default="0"), fallback=0.0),
        "instrumentalness": _safe_float_text(_first_non_empty(raw, ["instrumentalness"], default="0"), fallback=0.0),
        "liveness": _safe_float_text(_first_non_empty(raw, ["liveness"], default="0"), fallback=0.0),
        "valence": _safe_float_text(_first_non_empty(raw, ["valence"], default="0"), fallback=0.0),
        "tempo": _safe_float_text(_first_non_empty(raw, ["tempo"], default="120"), fallback=120.0),
    }

    try:
        if float(normalized["tempo"]) <= 0:
            return None
    except ValueError:
        return None

    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and normalize newer Spotify data into project schema.")
    parser.add_argument("--url", default=SOURCE_URL_DEFAULT, help="CSV URL to ingest")
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: project-root SpotifyAudioFeatures2020.csv)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing output file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[2]
    output_path = Path(args.output) if args.output else (project_root / "SpotifyAudioFeatures2020.csv")

    if output_path.exists() and not args.force:
        print(f"Output already exists: {output_path}")
        print("Use --force to overwrite.")
        return

    response = urlopen(args.url, timeout=30)
    raw_text = response.read().decode("utf-8", errors="replace").splitlines()
    reader = csv.DictReader(raw_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows_total = 0
    rows_written = 0
    rows_skipped = 0

    with output_path.open("w", encoding="utf-8", newline="") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()

        for row in reader:
            rows_total += 1
            normalized = _normalize_row(row)
            if normalized is None:
                rows_skipped += 1
                continue
            writer.writerow(normalized)
            rows_written += 1

    print(f"Source URL: {args.url}")
    print(f"Saved normalized dataset: {output_path}")
    print(f"Rows total: {rows_total}")
    print(f"Rows written: {rows_written}")
    print(f"Rows skipped: {rows_skipped}")


if __name__ == "__main__":
    main()
