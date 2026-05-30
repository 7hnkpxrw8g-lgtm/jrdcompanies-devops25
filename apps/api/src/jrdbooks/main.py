"""FastAPI app factory."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .logging_config import configure_logging
from .routers import (
    accounts,
    audit,
    auth,
    banking,
    bills,
    customers,
    dashboard,
    imports,
    invoices,
    journals,
    organizations,
    periods,
    reports,
)

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", environment=settings.environment, app=settings.app_name)
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0.1,
                environment=settings.environment,
            )
            logger.info("sentry.initialized")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("sentry.init_failed", error=str(exc))
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="JRDbooks API",
        version="0.1.0",
        description="Accounting platform — double-entry ledger, multi-entity, audit-grade.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception("request.unhandled", error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"detail": "internal_server_error", "request_id": rid},
            )
        duration_ms = (time.monotonic() - start) * 1000
        response.headers["x-request-id"] = rid
        logger.info(
            "request.completed",
            method=request.method,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response

    app.include_router(auth.router)
    app.include_router(organizations.router)
    app.include_router(accounts.router)
    app.include_router(journals.router)
    app.include_router(customers.router)
    app.include_router(invoices.router)
    app.include_router(banking.router)
    app.include_router(reports.router)
    app.include_router(dashboard.router)
    app.include_router(audit.router)
    app.include_router(bills.router)
    app.include_router(imports.router)
    app.include_router(periods.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "version": "0.1.0", "environment": settings.environment}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "name": "JRDbooks API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


app = create_app()
