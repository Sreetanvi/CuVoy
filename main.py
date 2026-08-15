"""CuVoy FastAPI entrypoint — Render web service, no workers (PROJECT_SPEC §16, §7.17)."""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai_gateway.gateway import AIGateway
from app.api.router import router
from app.config import get_settings
from app.jsonlog import configure_logging
from app.middleware import RequestIdMiddleware
from app.providers.client import ExternalData
from app.services.runtime import build_cache, build_supabase, new_http_client

logger = logging.getLogger("cuvoy")

_VERCEL_PREVIEW = r"https://.*\.vercel\.app"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    http = new_http_client()
    app.state.http = http
    app.state.cache = build_cache(settings, http)
    app.state.supabase = build_supabase(settings, http)
    app.state.ai_gateway = AIGateway(settings, http, app.state.cache)
    app.state.external = ExternalData(settings, http, app.state.cache)
    logger.info("startup")
    try:
        yield
    finally:
        await http.aclose()
        logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    if settings.sentry_dsn and "pytest" not in sys.modules:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.0)

    app = FastAPI(
        title="CuVoy API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=_VERCEL_PREVIEW,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "Idempotency-Key"],
    )
    app.include_router(router)
    return app


app = create_app()
