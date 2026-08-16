from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .routes_reviews import router as reviews_router

from .config import load_settings
from .logging_config import configure_logging
from .db import db_healthcheck, init_db
from .routes_subscribers import router as subscribers_router
from .routes_newsletters import router as newsletters_router
from .routes_workflows import router as workflows_router
from .routes_drafts import router as drafts_router
from .routes_ai import router as ai_router
from .routes_automation import router as automation_router

import structlog

configure_logging()
log = structlog.get_logger(__name__)
settings = load_settings()

app = FastAPI(
    title="Newsletter Orchestrator Backend",
    version="0.8.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    log.info("startup_db_initialized")


@app.get("/health", tags=["system"])
def health() -> JSONResponse:
    try:
        db_ok = db_healthcheck()
    except Exception as exc:  # noqa: BLE001
        log.error("health_db_check_failed", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unhealthy"},
        )

    status = "ok" if db_ok else "degraded"
    log.info("health_check", status=status, db=db_ok)

    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": status, "db": "healthy" if db_ok else "unhealthy"},
    )


app.include_router(subscribers_router)
app.include_router(newsletters_router)
app.include_router(workflows_router)
app.include_router(drafts_router)
app.include_router(ai_router)
app.include_router(automation_router)
app.include_router(reviews_router)
