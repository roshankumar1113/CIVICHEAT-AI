from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import IntegrationStatus, SystemStatusResponse
from app.services.integration_state import get_integration_state

router = APIRouter()


@router.get("/system/status", response_model=SystemStatusResponse, tags=["System"])
async def system_status():
    """
    Returns current system and integration status.

    `*_configured` reports whether credentials are present. The `fortyguard`
    and `nemotron` objects report the last *observed* outcome of real calls, so
    the dashboard can show CONNECTED only when a call has actually succeeded.
    Reading this endpoint never triggers an upstream request of its own.
    """
    settings = get_settings()
    from app.services.nemotron.nemotron_client import NemotronClient

    nemotron_client = NemotronClient()
    fortyguard_configured = bool(settings.fortyguard_api_key)
    nemotron_configured = nemotron_client.is_configured()

    observed = get_integration_state()

    return SystemStatusResponse(
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        fortyguard_configured=fortyguard_configured,
        nemotron_configured=nemotron_configured,
        demo_mode=not fortyguard_configured,
        tracks=["Track 4 - Government & Environment", "Track 6 - Agentic AI"],
        nemotron_model=nemotron_client.model if nemotron_configured else "",
        fortyguard=IntegrationStatus(
            configured=fortyguard_configured,
            **observed.fortyguard.as_dict(fortyguard_configured),  # type: ignore[arg-type]
        ),
        nemotron=IntegrationStatus(
            configured=nemotron_configured,
            **observed.nemotron.as_dict(nemotron_configured),  # type: ignore[arg-type]
        ),
    )
