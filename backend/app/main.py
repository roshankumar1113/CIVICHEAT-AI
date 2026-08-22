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


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"FortyGuard configured: {bool(settings.fortyguard_api_key)}")
    logger.info(f"Nemotron configured: {bool(settings.nemotron_base_url)}")
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
    allow_origins=settings.allowed_origins,
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
