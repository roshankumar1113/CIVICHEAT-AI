from fastapi import APIRouter
from app.core.config import get_settings
from app.schemas.common import SystemStatusResponse

router = APIRouter()


@router.get("/system/status", response_model=SystemStatusResponse, tags=["System"])
async def system_status():
    """Returns current system and integration status."""
    settings = get_settings()
    from app.services.nemotron.nemotron_client import NemotronClient
    nemotron_client = NemotronClient()
    return SystemStatusResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        fortyguard_configured=bool(settings.fortyguard_api_key),
        nemotron_configured=nemotron_client.is_configured(),
        demo_mode=not bool(settings.fortyguard_api_key),
        tracks=["Track 4 - Government & Environment", "Track 6 - Agentic AI"],
    )
