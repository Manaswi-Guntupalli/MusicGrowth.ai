from __future__ import annotations

import csv
import json
from pathlib import Path

from app.services.feature_extraction import extract_features_from_path
from app.services.normalization import normalize_features


def build_dataset(input_csv: Path, output_json: Path) -> None:
    rows: list[dict] = []
    with input_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio_path = row["audio_path"]
            raw = extract_features_from_path(audio_path, segment_mode="best")
            normalized = normalize_features(raw)
            rows.append(
                {
                    "artist": row["artist"],
                    "song": row["song"],
                    "cluster": row["cluster"],
                    "features": {
                        "tempo": normalized["tempo"],
                        "energy": normalized["energy"],
                        "danceability": normalized["danceability"],
                        "valence": normalized["valence"],
                        "acousticness": normalized["acousticness"],
                        "instrumentalness": normalized["instrumentalness"],
                        "speechiness": normalized["speechiness"],
                        "loudness": normalized["loudness"],
                        "liveness": normalized["liveness"],
                    },
                }
            )

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with output_json.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    input_path = Path("reference_songs.csv")
    output_path = Path("app/data/reference_dataset.json")
    build_dataset(input_path, output_path)
    print(f"Reference dataset updated at {output_path}")
