from pydantic import BaseModel, Field
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class IntegrationStatus(BaseModel):
    """
    Observed connectivity for one upstream integration.

    `configured` reports whether credentials exist. `state` reports what the
    backend has actually seen happen — the dashboard must use `state`, never
    `configured`, to decide whether to show CONNECTED.
    """

    configured: bool
    state: str = Field(
        ...,
        description=(
            "NOT_CONFIGURED | UNVERIFIED | CONNECTED | DEGRADED | "
            "AUTH_ERROR | TIMEOUT | UNAVAILABLE"
        ),
    )
    detail: Optional[str] = None
    checked_at: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0


class SystemStatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    fortyguard_configured: bool
    nemotron_configured: bool
    demo_mode: bool
    tracks: list[str]
    # Observed integration state — added so the dashboard can distinguish
    # "credentials present" from "integration actually working".
    nemotron_model: str = ""
    fortyguard: Optional[IntegrationStatus] = None
    nemotron: Optional[IntegrationStatus] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
