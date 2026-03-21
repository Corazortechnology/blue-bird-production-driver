"""
Driver Safety System – Complete Pipeline (per PDF).
APIs: /api/login, /api/monitor, /api/alerts, /api/safety-score + sessions.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import alerts, login, monitor, safety_score, sessions
from data_pipeline import websocket
from utils.logger import get_logger

logger = get_logger(__name__)


class AppFactory:
    """Application factory for production deployment."""

    @staticmethod
    def create() -> FastAPI:
        application = FastAPI(
            title="Driver Safety System",
            description="Complete pipeline: data ingestion, fusion, alerts, safety scoring",
            version="1.0.0",
        )
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        application.include_router(login.router)
        application.include_router(sessions.router)
        application.include_router(monitor.router)
        application.include_router(alerts.router)
        application.include_router(safety_score.router)
        application.include_router(websocket.router)
        logger.info("FastAPI application created — all routers registered")
        return application


app = AppFactory.create()

# Project root: app/api/main.py -> parents[2]
_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"


@app.get("/demo", include_in_schema=True)
async def browser_demo():
    """Single-page WebSocket demo (camera → /stream). Open in browser: /demo"""
    demo_path = _STATIC_DIR / "demo.html"
    if not demo_path.is_file():
        return {"error": "static/demo.html not found", "path": str(demo_path)}
    return FileResponse(demo_path, media_type="text/html")


@app.get("/")
def root():
    return {
        "service": "Driver Safety System",
        "apis": [
            "POST /api/login/",
            "POST /api/login/register",
            "POST /api/sessions/start",
            "POST /api/sessions/end",
            "POST /api/monitor/frame",
            "POST /api/alerts/",
            "GET /api/alerts/",
            "GET /api/safety-score/",
            "POST /api/safety-score/compute",
        ],
        "docs": "/docs",
        "browser_demo": "/demo",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting uvicorn server on 0.0.0.0:5000")
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        reload_dirs=["app", "data_pipeline", "database", "src", "training", "utils", "configs"],
    )
