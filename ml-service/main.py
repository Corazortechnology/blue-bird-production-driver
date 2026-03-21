"""
ML service — FastAPI + RetinaFace + TensorFlow (CPU).
Expose POST /analyze for internal calls from the API gateway.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

app = FastAPI(title="Blue Bird ML Service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze() -> dict[str, Any]:
    """
    Stub endpoint for internal API tests.
    Add RetinaFace + TensorFlow + multipart image handling here next.
    """
    return {"status": "ok", "service": "ml-service"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
