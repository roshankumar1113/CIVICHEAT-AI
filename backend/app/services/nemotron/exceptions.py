"""Nemotron-specific exceptions."""
from __future__ import annotations


class NemotronUnavailableError(Exception):
    """Raised when Nemotron endpoint is unreachable or not configured."""


class NemotronAuthError(NemotronUnavailableError):
    """
    Raised on 401/403 from Nemotron.

    Subclasses NemotronUnavailableError so that an expired, revoked, or
    credit-exhausted API key degrades into the deterministic fallback
    (like any other unavailability) instead of surfacing as HTTP 500.
    Handlers that need to distinguish auth failures must catch this
    before NemotronUnavailableError.
    """


class NemotronTimeoutError(Exception):
    """Raised when Nemotron inference times out."""


class NemotronMalformedResponseError(Exception):
    """Raised when the model returns unparseable or invalid-schema JSON."""


class NemotronToolError(Exception):
    """Raised when a tool call fails during the agent loop."""
