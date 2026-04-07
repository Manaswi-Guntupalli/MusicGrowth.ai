from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.services.trajectory import train_trajectory_surrogate_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the trajectory surrogate model for A/B optimization.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing surrogate artifacts and retrain from scratch.",
    )
    args = parser.parse_args()

    metadata = train_trajectory_surrogate_model(force_retrain=args.force)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
