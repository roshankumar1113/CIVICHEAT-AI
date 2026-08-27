"""
CIVICHEAT integration state recorder.

The dashboard must never claim an integration is CONNECTED just because an API
key is present in the environment. "Configured" is not "working".

This module keeps the last *observed* outcome of real calls to FortyGuard and
Nemotron. The FortyGuard service and the Nemotron client record here whenever
they actually succeed or fail, so GET /api/system/status can report what the
backend genuinely knows — without firing extra probe requests of its own.

State meanings
--------------
NOT_CONFIGURED  Credentials are missing. No call has been or can be made.
UNVERIFIED      Configured, but no call has been attempted yet this process.
CONNECTED       A real call succeeded.
DEGRADED        The integration answered, but the result was unusable and the
                deterministic/demo path was used instead.
AUTH_ERROR      Credentials were rejected (401/403).
TIMEOUT         The call exceeded its timeout.
UNAVAILABLE     Unreachable, or returned an error status.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

IntegrationStateName = Literal[
    "NOT_CONFIGURED",
    "UNVERIFIED",
    "CONNECTED",
    "DEGRADED",
    "AUTH_ERROR",
    "TIMEOUT",
    "UNAVAILABLE",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class IntegrationRecord:
    """Last observed outcome for a single upstream integration."""

    state: IntegrationStateName = "UNVERIFIED"
    detail: str | None = None
    checked_at: str | None = None
    success_count: int = 0
    failure_count: int = 0

    def _set(self, state: IntegrationStateName, detail: str | None) -> None:
        self.state = state
        # Keep details short — this is surfaced in a UI, not a log.
        self.detail = detail[:200] if detail else None
        self.checked_at = _now_iso()

    def record_success(self, detail: str | None = None) -> None:
        self.success_count += 1
        self._set("CONNECTED", detail)

    def record_degraded(self, detail: str | None = None) -> None:
        self.failure_count += 1
        self._set("DEGRADED", detail)

    def record_auth_error(self, detail: str | None = None) -> None:
        self.failure_count += 1
        self._set("AUTH_ERROR", detail)

    def record_timeout(self, detail: str | None = None) -> None:
        self.failure_count += 1
        self._set("TIMEOUT", detail)

    def record_unavailable(self, detail: str | None = None) -> None:
        self.failure_count += 1
        self._set("UNAVAILABLE", detail)

    def as_dict(self, configured: bool) -> dict[str, object]:
        """
        Project the record for API output.

        When credentials are absent the observed state is irrelevant — the
        honest answer is NOT_CONFIGURED.
        """
        state: IntegrationStateName = self.state if configured else "NOT_CONFIGURED"
        return {
            "state": state,
            "detail": self.detail if configured else "Credentials not configured.",
            "checked_at": self.checked_at,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


@dataclass
class IntegrationState:
    """Process-wide observed state for every upstream CIVICHEAT depends on."""

    fortyguard: IntegrationRecord = field(default_factory=IntegrationRecord)
    nemotron: IntegrationRecord = field(default_factory=IntegrationRecord)

    def reset(self) -> None:
        self.fortyguard = IntegrationRecord()
        self.nemotron = IntegrationRecord()


_lock = threading.Lock()
_state = IntegrationState()


def get_integration_state() -> IntegrationState:
    """Module-level singleton — mirrors the other CIVICHEAT service singletons."""
    return _state


def reset_integration_state() -> None:
    with _lock:
        _state.reset()
