"""
FortyGuard async HTTP client.

Authentication: api-key header (verified).
Never logs API key values.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.fortyguard.fortyguard_models import (
    ActivityStatusResponse,
    HeatmapRequest,
    HeatmapSubmitResponse,
)

logger = logging.getLogger(__name__)

# Polling config
_POLL_INITIAL_DELAY = 2.0   # seconds before first poll
_POLL_INTERVAL = 3.0        # seconds between polls
_POLL_MAX_ATTEMPTS = 20     # max ~60 s total wait
_TERMINAL_STATUSES = {"Completed", "Failed", "Error"}


class FortyGuardAPIError(Exception):
    """Raised when FortyGuard returns an error response."""
    def __init__(self, status_code: int, message: str, detail: Any = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail
        super().__init__(f"FortyGuard API error {status_code}: {message}")


class FortyGuardTimeoutError(Exception):
    """Raised when activity polling exceeds the maximum wait time."""


class FortyGuardClient:
    """
    Async client for the FortyGuard Temperature API.

    Usage:
        async with FortyGuardClient() as client:
            intelligence = await client.get_heat_intelligence(request)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._client: httpx.AsyncClient | None = None

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._settings.fortyguard_base_url,
            headers={
                "api-key": self._settings.fortyguard_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(15.0),
        )

    async def __aenter__(self) -> "FortyGuardClient":
        self._client = self._make_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("FortyGuardClient must be used as async context manager")
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_heatmap(self, request: HeatmapRequest) -> str:
        """
        Submit a heatmap job.
        Returns activity_id on success.
        Raises FortyGuardAPIError on failure.
        """
        client = self._get_client()
        payload = request.model_dump(exclude_none=True)
        logger.info(
            "FortyGuard: submitting heatmap | city_polygon=%s | date=%s",
            str(payload["polygon_aoi"])[:80],
            payload["date_time"].get("start_date"),
        )

        try:
            response = await client.post("/v1/heatmap", json=payload)
        except httpx.TimeoutException as exc:
            raise FortyGuardAPIError(408, "Request timed out") from exc
        except httpx.RequestError as exc:
            raise FortyGuardAPIError(503, f"Network error: {exc}") from exc

        self._raise_for_error(response)

        data = HeatmapSubmitResponse.model_validate(response.json())
        activity_id = data.data.activity_id
        logger.info("FortyGuard: activity submitted | activity_id=%s", activity_id)
        return activity_id

    async def get_activity_status(self, activity_id: str) -> ActivityStatusResponse:
        """Poll the status of an activity."""
        client = self._get_client()
        try:
            response = await client.get(f"/v1/status/{activity_id}")
        except httpx.TimeoutException as exc:
            raise FortyGuardAPIError(408, "Status poll timed out") from exc
        except httpx.RequestError as exc:
            raise FortyGuardAPIError(503, f"Network error during poll: {exc}") from exc

        self._raise_for_error(response)
        return ActivityStatusResponse.model_validate(response.json())

    async def wait_for_result(self, activity_id: str) -> ActivityStatusResponse:
        """
        Poll until activity reaches a terminal status.
        Uses fixed interval polling (simple and reliable for hackathon).
        Raises FortyGuardTimeoutError if max attempts exceeded.
        """
        logger.info(
            "FortyGuard: polling activity | activity_id=%s | max_attempts=%d",
            activity_id,
            _POLL_MAX_ATTEMPTS,
        )
        await asyncio.sleep(_POLL_INITIAL_DELAY)

        for attempt in range(1, _POLL_MAX_ATTEMPTS + 1):
            status_response = await self.get_activity_status(activity_id)
            current_status = status_response.data.status
            logger.info(
                "FortyGuard: poll %d/%d | activity_id=%s | status=%s",
                attempt,
                _POLL_MAX_ATTEMPTS,
                activity_id,
                current_status,
            )

            if current_status in _TERMINAL_STATUSES:
                if current_status != "Completed":
                    raise FortyGuardAPIError(
                        422,
                        f"Activity failed with status: {current_status}",
                        {"activity_id": activity_id},
                    )
                return status_response

            if attempt < _POLL_MAX_ATTEMPTS:
                await asyncio.sleep(_POLL_INTERVAL)

        raise FortyGuardTimeoutError(
            f"Activity {activity_id} did not complete after "
            f"{_POLL_MAX_ATTEMPTS} polls ({_POLL_MAX_ATTEMPTS * _POLL_INTERVAL:.0f}s)"
        )

    async def get_heat_intelligence(self, request: HeatmapRequest) -> ActivityStatusResponse:
        """
        Full pipeline: submit → poll → return completed result.
        This is the primary entry point for the rest of the application.
        """
        activity_id = await self.create_heatmap(request)
        return await self.wait_for_result(activity_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
            message = body.get("message") or body.get("details", {}).get("message", "Unknown error")
        except Exception:
            message = response.text[:200] or f"HTTP {response.status_code}"
        raise FortyGuardAPIError(response.status_code, message, response.text[:500])
