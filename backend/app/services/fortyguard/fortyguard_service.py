"""
FortyGuard service layer.
Orchestrates the client + parser.
This is what the rest of the app calls — not the client directly.
"""
from __future__ import annotations

import logging

from app.core.config import get_settings
from app.services.fortyguard.fortyguard_client import (
    FortyGuardAPIError,
    FortyGuardClient,
    FortyGuardTimeoutError,
)
from app.services.fortyguard.fortyguard_models import (
    DateTimeFilter,
    GeoJSONPolygon,
    HeatIntelligence,
    HeatmapRequest,
)
from app.services.fortyguard.fortyguard_parser import (
    build_demo_intelligence,
    parse_heat_intelligence,
)

logger = logging.getLogger(__name__)

# Phoenix, AZ — default U.S. demo city
PHOENIX_POLYGON = GeoJSONPolygon(
    type="Polygon",
    coordinates=[[
        [-112.0740, 33.4484],
        [-112.0540, 33.4484],
        [-112.0540, 33.4284],
        [-112.0740, 33.4284],
        [-112.0740, 33.4484],
    ]],
)


class FortyGuardService:
    """
    High-level FortyGuard service.
    Handles live vs demo mode automatically based on config.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def is_configured(self) -> bool:
        return bool(self._settings.fortyguard_api_key)

    async def get_heat_intelligence(
        self,
        city: str = "Phoenix, AZ",
        date: str = "2025-08-01",
        polygon: GeoJSONPolygon | None = None,
        use_demo_fallback: bool = True,
    ) -> HeatIntelligence:
        """
        Get heat intelligence for a city.

        If FortyGuard is not configured (no API key), returns demo data.
        If FortyGuard fails and use_demo_fallback=True, returns demo data with a warning.
        """
        if not self.is_configured():
            logger.warning(
                "FortyGuard: API key not configured — returning DEMO intelligence"
            )
            return build_demo_intelligence(city=city, date=date)

        request = HeatmapRequest(
            polygon_aoi=polygon or PHOENIX_POLYGON,
            date_time=DateTimeFilter(start_date=date, filter_type=3),
        )

        try:
            async with FortyGuardClient() as client:
                status_response = await client.get_heat_intelligence(request)
            return parse_heat_intelligence(status_response, city=city, date=date)

        except (FortyGuardAPIError, FortyGuardTimeoutError) as exc:
            logger.error("FortyGuard: live request failed | error=%s", exc)
            if use_demo_fallback:
                logger.warning("FortyGuard: falling back to DEMO intelligence")
                demo = build_demo_intelligence(city=city, date=date)
                # Mark it clearly so the UI can show the fallback state
                demo.data_mode = "DEMO"
                return demo
            raise


# Module-level singleton
_service: FortyGuardService | None = None


def get_fortyguard_service() -> FortyGuardService:
    global _service
    if _service is None:
        _service = FortyGuardService()
    return _service
