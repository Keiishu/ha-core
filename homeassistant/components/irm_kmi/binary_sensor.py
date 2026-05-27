"""Support for IRM KMI warning binary sensors."""

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import IrmKmiConfigEntry
from .entity import IrmKmiBaseEntity
from .warning import format_warning, is_warning_active

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: IrmKmiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    async_add_entities([IrmKmiWarningBinarySensor(entry)])


class IrmKmiWarningBinarySensor(IrmKmiBaseEntity, BinarySensorEntity):
    """Representation of an IRM KMI weather warning."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_translation_key = "warning"

    def __init__(self, entry: IrmKmiConfigEntry) -> None:
        """Initialize the warning binary sensor."""
        super().__init__(entry)
        self._attr_unique_id = f"{entry.data[CONF_UNIQUE_ID]}_warning"

    @property
    def is_on(self) -> bool:
        """Return whether there are active warnings."""
        now = dt_util.now()
        return any(
            is_warning_active(warning, now)
            for warning in self.coordinator.data.warnings
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the warning sensor attributes."""
        now = dt_util.now()
        warnings = [
            format_warning(warning, now) for warning in self.coordinator.data.warnings
        ]
        active_warning_names = [
            warning["friendly_name"]
            for warning in warnings
            if warning["is_active"] and warning["friendly_name"]
        ]

        return {
            "warnings": warnings,
            "active_warnings_friendly_names": ", ".join(active_warning_names),
        }
