from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers.analysis import router as analysis_router
from backend.app.routers.auth import router as auth_router


class FakeInsertOneResult:
    def __init__(self, inserted_id: ObjectId):
        self.inserted_id = inserted_id


class FakeCursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs
        self._index = 0

    def sort(self, field: str, direction: int):
        reverse = direction < 0
        self._docs.sort(key=lambda d: d.get(field, datetime.now(UTC)), reverse=reverse)
        return self

    def limit(self, value: int):
        if value > 0:
            self._docs = self._docs[:value]
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._docs):
            raise StopAsyncIteration
        item = self._docs[self._index]
        self._index += 1
        return item


class FakeCollection:
    def __init__(self):
        self.docs: list[dict[str, Any]] = []

    async def create_index(self, *_args, **_kwargs):
        return None

    async def find_one(self, query: dict[str, Any]):
        for doc in self.docs:
            if _matches(doc, query):
                return dict(doc)
        return None

    async def insert_one(self, doc: dict[str, Any]):
        stored = dict(doc)
        stored.setdefault("_id", ObjectId())
        self.docs.append(stored)
        return FakeInsertOneResult(stored["_id"])

    def find(self, query: dict[str, Any]):
        filtered = [dict(doc) for doc in self.docs if _matches(doc, query)]
        return FakeCursor(filtered)


class FakeDB:
    def __init__(self):
        self.users = FakeCollection()
        self.song_analyses = FakeCollection()


def _matches(doc: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, value in query.items():
        if doc.get(key) != value:
            return False
    return True


@pytest.fixture()
def fake_db() -> FakeDB:
    return FakeDB()


@pytest.fixture()
def sample_analysis_result() -> dict[str, Any]:
    return {
        "sound_dna": {
            "tempo": 128.5,
            "energy": 0.77,
            "danceability": 0.71,
            "valence": 0.52,
            "acousticness": 0.14,
            "instrumentalness": 0.11,
            "speechiness": 0.08,
            "loudness": -7.2,
            "liveness": 0.21,
            "mfcc_mean_1": -20.1,
            "mfcc_mean_2": 10.2,
            "mfcc_mean_3": 2.5,
            "mfcc_mean_4": 7.8,
            "mfcc_mean_5": -3.1,
            "production_style": "Balanced indie",
            "mood": "Reflective / balanced",
        },
        "style_cluster": {
            "cluster_id": 2,
            "label": "Balanced Indie - Mid Tempo / Synth Tilt / Neutral",
            "confidence": 68.2,
            "raw_confidence": 74.9,
        },
        "top_similar": [
            {
                "artist": "Artist A",
                "song": "Track A",
                "cluster": "Balanced Indie",
                "similarity": 82.1,
            }
        ],
        "differences": [
            {
                "feature": "energy",
                "tag": "KEY_DIFFERENTIATOR",
                "song_value": 0.77,
                "reference_mean": 0.69,
                "delta_percent": 8.0,
                "interpretation": "Slightly higher than cluster mean.",
            }
        ],
        "market_gaps": ["Moderate opportunity in current cluster."],
        "paths": [
            {
                "id": "A",
                "title": "Mainstream Acceleration",
                "strategy": "Move closer to high-discoverability profiles.",
                "expected": "Faster pickup.",
                "tradeoff": "Higher competition.",
                "actions": ["Tighten hooks", "Increase energy"],
            }
        ],
    }


@pytest.fixture()
def test_client(fake_db: FakeDB, sample_analysis_result: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("backend.app.routers.auth.get_db", lambda: fake_db)
    monkeypatch.setattr("backend.app.dependencies.auth.get_db", lambda: fake_db)
    monkeypatch.setattr("backend.app.routers.analysis.get_db", lambda: fake_db)

    monkeypatch.setattr("backend.app.routers.analysis._validate_uploaded_audio_file", lambda _path: None)
    monkeypatch.setattr("backend.app.routers.analysis.run_analysis", lambda *_args, **_kwargs: dict(sample_analysis_result))

    app = FastAPI(title="MusicGrowth.AI Test App")
    app.include_router(auth_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")

    return TestClient(app)
