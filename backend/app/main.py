import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes import health, system, heatmap, risk, analysis, agent, reassessment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def _probe_fortyguard() -> None:
    """Ping FortyGuard on startup to establish real connection state."""
    from app.services.fortyguard.fortyguard_service import get_fortyguard_service
    from app.services.integration_state import get_integration_state
    service = get_fortyguard_service()
    if not service.is_configured():
        get_integration_state().fortyguard.record_unavailable("API key not configured.")
        logger.info("FortyGuard: not configured — skipping probe")
        return
    try:
        # Lightweight probe: submit a real job and parse the result
        intelligence = await service.get_heat_intelligence(
            city="Phoenix, AZ", date="2025-08-01", use_demo_fallback=False
        )
        # record_success is called inside get_heat_intelligence on success
        logger.info("FortyGuard: startup probe succeeded — %d tiles", intelligence.tile_count)
    except Exception as exc:
        logger.warning("FortyGuard: startup probe failed — %s", exc)


async def _probe_nemotron() -> None:
    """Ping Nemotron on startup to establish real connection state."""
    from app.services.nemotron.nemotron_client import NemotronClient
    from app.services.integration_state import get_integration_state
    client = NemotronClient()
    if not client.is_configured():
        get_integration_state().nemotron.record_unavailable("API key not configured.")
        logger.info("Nemotron: not configured — skipping probe")
        return
    try:
        async with NemotronClient() as c:
            result = await c.health_check()
        if result.get("status") == "ok":
            get_integration_state().nemotron.record_success(
                f"Model {result.get('model', 'unknown')} responded to startup probe."
            )
            logger.info("Nemotron: startup probe succeeded — model=%s", result.get("model"))
        else:
            get_integration_state().nemotron.record_unavailable(result.get("detail", "Probe failed."))
            logger.warning("Nemotron: startup probe returned non-ok — %s", result)
    except Exception as exc:
        logger.warning("Nemotron: startup probe failed — %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clear settings cache so the new .env values are picked up cleanly
    get_settings.cache_clear()
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"FortyGuard configured: {bool(settings.fortyguard_api_key)}")
    logger.info(f"Nemotron configured: {bool(settings.nemotron_base_url)}")

    # Fire both probes concurrently — they are independent
    asyncio.create_task(_probe_fortyguard())
    asyncio.create_task(_probe_nemotron())

    yield
    logger.info("Shutting down CIVICHEAT AI")


settings = get_settings()

app = FastAPI(
    title="CIVICHEAT AI",
    description=(
        "Autonomous AI Heat-Response System for Government\n\n"
        "**Track 4** — Government & Environment  \n"
        "**Track 6** — Agentic AI"
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if settings.allowed_origins else ["*"],
    allow_origin_regex=r"https://.*(\.vercel\.app|\.onrender\.com|\.railway\.app|\.pages\.dev|\.netlify\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(heatmap.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(reassessment.router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "CIVICHEAT AI",
        "description": "Autonomous AI Heat-Response System for Government",
        "status": "online",
        "docs": "/api/docs",
        "tracks": ["Track 4 - Government & Environment", "Track 6 - Agentic AI"],
    }
