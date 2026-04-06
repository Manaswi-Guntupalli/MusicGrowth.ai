import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient

BACKEND_ROOT = Path(__file__).resolve().parent / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schemas import AnalysisHistoryItem, AnalysisResponse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate analysis history documents with Pydantic schemas.")
    parser.add_argument("--user-id", default=os.getenv("DEBUG_USER_ID") or os.getenv("USER_ID"))
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
    parser.add_argument("--db-name", default=os.getenv("MONGO_DB_NAME", "musicgrowth"))
    parser.add_argument("--limit", type=int, default=100, help="Max docs to validate")
    return parser.parse_args()


def resolve_user_id(raw_user_id: str | None) -> ObjectId:
    if not raw_user_id:
        raise SystemExit("Missing user id. Pass --user-id or set DEBUG_USER_ID/USER_ID.")

    try:
        return ObjectId(raw_user_id)
    except InvalidId as exc:
        raise SystemExit(f"Invalid user id '{raw_user_id}': {exc}") from exc

def main() -> None:
    args = parse_args()
    uid = resolve_user_id(args.user_id)
    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    bad = 0
    count = 0
    cursor = db.song_analyses.find({"user_id": uid}).sort("created_at", -1)
    if args.limit > 0:
        cursor = cursor.limit(args.limit)

    for doc in cursor:
        count += 1
        sound_dna = doc.get("result", {}).get("sound_dna", {})
        parsed_result = None
        if doc.get("result"):
            try:
                parsed_result = AnalysisResponse(**doc["result"])
            except Exception:
                parsed_result = None

        try:
            AnalysisHistoryItem(
                id=str(doc["_id"]),
                filename=doc.get("filename", "upload"),
                segment_mode=doc.get("segment_mode", "best"),
                mood=sound_dna.get("mood", "Unknown"),
                production_style=sound_dna.get("production_style", "Unknown"),
                created_at=doc.get("created_at", datetime.now(UTC)),
                result=parsed_result,
            )
        except Exception as exc:
            bad += 1
            print("BAD_DOC", doc.get("_id"), type(exc).__name__, str(exc))

    print("checked", count, "bad", bad)


if __name__ == "__main__":
    main()
