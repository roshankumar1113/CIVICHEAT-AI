from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class SystemStatusResponse(BaseModel):
    app_name: str
    version: str
    environment: str
    fortyguard_configured: bool
    nemotron_configured: bool
    demo_mode: bool
    tracks: list[str]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
