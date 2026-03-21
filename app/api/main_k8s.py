"""
Thin API for Kubernetes — FastAPI + httpx only (no ML imports).

Use this image until you refactor heavy routes (login/monitor) to call ML_URL.
Full app: main.py (requires full repo + DB + ML stack in-process).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import FastAPI

ML_URL = os.environ.get("ML_URL", "http://ml-service:8001/analyze")

app = FastAPI(
    title="Driver Safety API (K8s thin mode)",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "k8s-thin"}


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "api-service",
        "mode": "k8s-thin",
        "ml_url": ML_URL,
        "note": "Full /api/* routes need DB + refactor; use /test-ml for internal ML check",
    }


@app.post("/test-ml")
async def test_ml() -> dict[str, Any]:
    """Verify API → ml-service over Cluster DNS."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(ML_URL)
        r.raise_for_status()
        return {"upstream_status": r.status_code, "body": r.json()}
