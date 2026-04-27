from __future__ import annotations


class SourceUnavailableError(RuntimeError):
    """Raised when a source cannot provide data due to transient unavailability."""
