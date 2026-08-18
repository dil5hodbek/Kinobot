"""Health-check + metrics HTTP serveri (aiohttp — aiogram bilan birga keladi).

Endpointlar:
  GET /health/live   — jarayon tirikmi (har doim 200; liveness probe)
  GET /health/ready  — bog'liqliklar tayyormi: PostgreSQL (SELECT 1) +
                       Redis (PING). Readiness probe / Docker healthcheck.
  GET /metrics       — Prometheus formatida metrikalar.

Webhook rejimida xuddi shu aiohttp ilovasiga aiogram webhook handleri ham
ulanadi (app/main.py) — bitta port, bitta server.
"""
from __future__ import annotations

import logging

from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


def build_app(engine: AsyncEngine, redis: Redis) -> web.Application:
    app = web.Application()

    async def live(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    async def ready(_request: web.Request) -> web.Response:
        problems: list[str] = []
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"postgres: {exc}")
        try:
            await redis.ping()
        except Exception as exc:  # noqa: BLE001
            problems.append(f"redis: {exc}")

        if problems:
            return web.Response(status=503, text="; ".join(problems))
        return web.Response(text="READY")

    async def metrics(_request: web.Request) -> web.Response:
        return web.Response(
            body=generate_latest(), content_type=CONTENT_TYPE_LATEST.split(";")[0]
        )

    app.router.add_get("/health/live", live)
    app.router.add_get("/health/ready", ready)
    app.router.add_get("/metrics", metrics)
    return app


async def start_http_server(
    app: web.Application, port: int
) -> web.AppRunner:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("HTTP server (health/metrics) %s portda ishga tushdi.", port)
    return runner
