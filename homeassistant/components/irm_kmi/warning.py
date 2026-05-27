"""Helpers for IRM KMI warnings."""

from datetime import datetime
from typing import Any

from irm_kmi_api import WarningData


def is_warning_active(warning: WarningData, now: datetime) -> bool:
    """Return whether the warning is currently active."""
    return warning["starts_at"] < now < warning["ends_at"]


def format_warning(warning: WarningData, now: datetime) -> dict[str, Any]:
    """Return warning data suitable for state attributes."""
    return {
        "slug": warning["slug"].value,
        "id": warning["id"],
        "level": warning["level"],
        "friendly_name": warning["friendly_name"],
        "text": warning["text"],
        "starts_at": warning["starts_at"].isoformat(),
        "ends_at": warning["ends_at"].isoformat(),
        "is_active": is_warning_active(warning, now),
    }
