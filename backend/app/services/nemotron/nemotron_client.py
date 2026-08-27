"""
CIVICHEAT Nemotron client.

Provider-agnostic: uses OpenAI-compatible /v1/chat/completions.
Configuration is 100% environment-variable driven — no hardcoded values.

Verified working endpoint: https://integrate.api.nvidia.com/v1
Verified working model:    nvidia/nemotron-mini-4b-instruct
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.nemotron.exceptions import (
    NemotronAuthError,
    NemotronMalformedResponseError,
    NemotronTimeoutError,
    NemotronUnavailableError,
)
from app.services.integration_state import get_integration_state
from app.services.nemotron.nemotron_models import ChatResponse

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60.0
_DEFAULT_MAX_TOKENS = 512


def _normalise_base_url(url: str) -> str:
    """
    Ensure the base URL ends with /v1 exactly once.
    Handles: https://integrate.api.nvidia.com/v1
             https://integrate.api.nvidia.com/v1/
             https://localhost:8080
    """
    url = url.rstrip("/")
    if not url.endswith("/v1"):
        url = url + "/v1"
    return url


class NemotronClient:
    """
    Async OpenAI-compatible client for Nemotron inference.

    Usage:
        async with NemotronClient() as client:
            response = await client.chat(messages=[...])
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = _normalise_base_url(settings.nemotron_base_url) if settings.nemotron_base_url else ""
        self._api_key = settings.nemotron_api_key
        self._model = settings.nemotron_model
        self._timeout = _DEFAULT_TIMEOUT
        self._http: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return bool(self._base_url and self._api_key)

    @property
    def model(self) -> str:
        """The model identifier this client will actually call (from NEMOTRON_MODEL)."""
        return self._model

    def _make_http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(self._timeout),
        )

    async def __aenter__(self) -> "NemotronClient":
        self._http = self._make_http_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("NemotronClient must be used as async context manager")
        return self._http

    async def chat(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = 0.1,
    ) -> ChatResponse:
        """Simple chat completion — no tools."""
        return await self._call(messages=messages, max_tokens=max_tokens, temperature=temperature)

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = 0.1,
        tool_choice: str | dict[str, Any] = "auto",
    ) -> ChatResponse:
        """
        Chat completion with tool definitions.

        tool_choice can be:
          "auto"     — model decides whether to call a tool
          "required" — model must call at least one tool
          {"type": "function", "function": {"name": "tool_name"}} — force specific tool
        """
        return await self._call(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def health_check(self) -> dict[str, Any]:
        """
        Verify the endpoint is reachable.
        Returns {"status": "ok", "model": ...} or {"status": "error", "detail": ...}
        """
        if not self.is_configured():
            return {"status": "not_configured", "detail": "NEMOTRON_BASE_URL or NEMOTRON_API_KEY not set"}
        try:
            resp = await self.chat(
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=5,
                temperature=0.0,
            )
            return {"status": "ok", "model": resp.model}
        except NemotronTimeoutError:
            return {"status": "timeout", "detail": "Nemotron inference timed out"}
        except NemotronAuthError:
            return {"status": "auth_error", "detail": "Authentication failed"}
        except NemotronUnavailableError as e:
            return {"status": "unavailable", "detail": str(e)}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _call(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] = "auto",
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = 0.1,
    ) -> ChatResponse:
        if not self.is_configured():
            raise NemotronUnavailableError("Nemotron is not configured (missing BASE_URL or API_KEY)")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        url = f"{self._base_url}/chat/completions"
        logger.info(
            "Nemotron: calling %s | model=%s | messages=%d",
            url,
            self._model,
            len(messages),
        )

        try:
            response = await self._client().post(url, json=payload)
        except httpx.TimeoutException as exc:
            get_integration_state().nemotron.record_timeout(
                f"Inference exceeded {self._timeout}s."
            )
            raise NemotronTimeoutError(f"Nemotron inference timed out after {self._timeout}s") from exc
        except httpx.RequestError as exc:
            get_integration_state().nemotron.record_unavailable(str(exc))
            raise NemotronUnavailableError(f"Cannot reach Nemotron: {exc}") from exc

        self._raise_for_status(response)

        try:
            data = response.json()
            parsed = ChatResponse.model_validate(data)
        except Exception as exc:
            get_integration_state().nemotron.record_degraded(
                "Model responded but the payload did not match the expected schema."
            )
            raise NemotronMalformedResponseError(
                f"Could not parse Nemotron response: {exc}\nRaw: {response.text[:500]}"
            ) from exc

        total_tokens = parsed.usage.total_tokens if parsed.usage else -1
        logger.info(
            "Nemotron: response | finish=%s | tokens=%d",
            parsed.choices[0].finish_reason if parsed.choices else "?",
            total_tokens,
        )
        get_integration_state().nemotron.record_success(f"Model {self._model} responded.")
        return parsed

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code in (401, 403):
            get_integration_state().nemotron.record_auth_error(
                f"Credentials rejected (HTTP {response.status_code})."
            )
            raise NemotronAuthError(f"Nemotron authentication failed: HTTP {response.status_code}")
        try:
            detail = response.json().get("detail") or response.json().get("message") or response.text[:300]
        except Exception:
            detail = response.text[:300]
        get_integration_state().nemotron.record_unavailable(
            f"HTTP {response.status_code}: {detail}"
        )
        raise NemotronUnavailableError(f"Nemotron API error {response.status_code}: {detail}")
