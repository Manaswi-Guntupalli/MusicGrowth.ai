from __future__ import annotations

import argparse
import json

from app.services.pipeline import run_analysis


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a local audio clip with MusicGrowth pipeline.")
    parser.add_argument("audio_path", help="Path to local audio file")
    parser.add_argument("--segment-mode", choices=["best", "full"], default="best")
    args = parser.parse_args()

    result = run_analysis(args.audio_path, segment_mode=args.segment_mode)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
