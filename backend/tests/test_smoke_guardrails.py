from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.app.main as main_module


def test_health_endpoint_smoke(monkeypatch: pytest.MonkeyPatch):
    async def _noop_init_indexes() -> None:
        return None

    monkeypatch.setattr(main_module, "validate_startup_environment", lambda: None)
    monkeypatch.setattr(main_module, "init_indexes", _noop_init_indexes)

    with TestClient(main_module.app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.skipif(os.name != "nt", reason="PowerShell startup smoke is Windows-only")
def test_start_dev_dry_run_smoke():
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "start-dev.ps1"

    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-DryRun",
            "-SkipInstall",
            "-SkipPreflight",
            "-NoBrowser",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    assert result.returncode == 0
    assert "Backend command:" in result.stdout
    assert "Frontend command:" in result.stdout
