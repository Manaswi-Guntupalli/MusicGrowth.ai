import argparse
import math
import os

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find analysis documents containing non-finite values.")
    parser.add_argument("--user-id", default=os.getenv("DEBUG_USER_ID") or os.getenv("USER_ID"))
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017"))
    parser.add_argument("--db-name", default=os.getenv("MONGO_DB_NAME", "musicgrowth"))
    parser.add_argument("--limit", type=int, default=0, help="Optional max number of docs to scan")
    return parser.parse_args()


def resolve_user_id(raw_user_id: str | None) -> ObjectId:
    if not raw_user_id:
        raise SystemExit("Missing user id. Pass --user-id or set DEBUG_USER_ID/USER_ID.")

    try:
        return ObjectId(raw_user_id)
    except InvalidId as exc:
        raise SystemExit(f"Invalid user id '{raw_user_id}': {exc}") from exc

def has_non_finite(value):
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(has_non_finite(v) for v in value.values())
    if isinstance(value, list):
        return any(has_non_finite(v) for v in value)
    return False


def main() -> None:
    args = parse_args()
    uid = resolve_user_id(args.user_id)
    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    cursor = db.song_analyses.find({"user_id": uid})
    if args.limit > 0:
        cursor = cursor.limit(args.limit)

    checked = 0
    bad: list[str] = []
    for doc in cursor:
        checked += 1
        res = doc.get("result", {})
        if has_non_finite(res):
            bad.append(str(doc.get("_id")))

    print("checked_docs", checked)
    print("non_finite_docs", len(bad))
    if bad:
        print("\n".join(bad))


if __name__ == "__main__":
    main()
