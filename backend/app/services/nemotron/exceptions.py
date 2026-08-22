"""Nemotron-specific exceptions."""
from __future__ import annotations


class NemotronUnavailableError(Exception):
    """Raised when Nemotron endpoint is unreachable or not configured."""


class NemotronAuthError(Exception):
    """Raised on 401/403 from Nemotron."""


class NemotronTimeoutError(Exception):
    """Raised when Nemotron inference times out."""


class NemotronMalformedResponseError(Exception):
    """Raised when the model returns unparseable or invalid-schema JSON."""


class NemotronToolError(Exception):
    """Raised when a tool call fails during the agent loop."""
