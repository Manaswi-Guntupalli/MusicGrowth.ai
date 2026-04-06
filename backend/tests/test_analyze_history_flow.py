from __future__ import annotations

from fastapi.testclient import TestClient


def _register_and_token(client: TestClient, email: str) -> str:
    payload = {"name": "Tester", "email": email, "password": "Passw0rd!"}
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    return response.json()["access_token"]


def test_analyze_and_history_contract(test_client: TestClient):
    token = _register_and_token(test_client, "analyze@example.com")

    files = {
        "file": (
            "demo.mp3",
            b"fake-audio-bytes-for-test",
            "audio/mpeg",
        )
    }

    analyze = test_client.post(
        "/api/analyze?segment_mode=best",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert analyze.status_code == 200

    body = analyze.json()
    assert "analysis_id" in body
    assert body["style_cluster"]["cluster_id"] == 2
    assert "raw_confidence" in body["style_cluster"]
    assert body["differences"][0]["tag"] == "KEY_DIFFERENTIATOR"

    history = test_client.get("/api/analyses", headers={"Authorization": f"Bearer {token}"})
    assert history.status_code == 200
    items = history.json()
    assert len(items) == 1
    assert items[0]["result"] is not None
    assert items[0]["result"]["style_cluster"]["label"]
