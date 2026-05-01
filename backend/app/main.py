"""
FastAPI application entry point.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.core.logging_config import configure_logging
from app.core.websocket import ws_manager
from app.database import engine
from app.models import (  # noqa: F401 — import models so Alembic sees them
    Campaign,
    CallLog,
    Lead,
    Reminder,
    User,
)

configure_logging()
log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.2,
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    log.info("startup.begin", env=settings.app_env)
    # Verify DB connectivity
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    log.info("startup.db_ok")
    yield
    await engine.dispose()
    log.info("shutdown.complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CallFlow-AI",
    description="AI SDR system for driving event attendance",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


# ---------------------------------------------------------------------------
# Request correlation ID middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def _correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
from app.api.auth import router as auth_router
from app.api.campaigns import router as campaigns_router
from app.api.calls import router as calls_router
from app.api.leads import router as leads_router
from app.api.webhooks import router as webhooks_router

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(campaigns_router, prefix="/campaigns", tags=["Campaigns"])
app.include_router(leads_router, prefix="/leads", tags=["Leads"])
app.include_router(calls_router, prefix="/calls", tags=["Calls"])
app.include_router(webhooks_router, prefix="/webhook", tags=["Webhooks"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "env": settings.app_env}


# ---------------------------------------------------------------------------
# WebSocket — Live call feed
# ---------------------------------------------------------------------------
@app.websocket("/ws/calls")
async def ws_live_calls(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client sends pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
