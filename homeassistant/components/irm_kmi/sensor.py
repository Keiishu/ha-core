"""Support for IRM KMI sensors."""

from datetime import datetime
from typing import Any

from irm_kmi_api import PollenName, PollenParser, RadarForecast

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import POLLEN_TO_ICON_MAP
from .coordinator import IrmKmiConfigEntry
from .entity import IrmKmiBaseEntity
from .warning import format_warning

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: IrmKmiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    async_add_entities(
        [
            *(IrmKmiPollenSensor(entry, pollen) for pollen in PollenName),
            IrmKmiCurrentRainfallSensor(entry),
            IrmKmiNextWarningSensor(entry),
        ]
    )


class IrmKmiPollenSensor(IrmKmiBaseEntity, SensorEntity):
    """Representation of a pollen sensor."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [level.value for level in PollenParser.get_option_values()]

    def __init__(self, entry: IrmKmiConfigEntry, pollen: PollenName) -> None:
        """Initialize the pollen sensor."""
        super().__init__(entry)
        self._attr_icon = POLLEN_TO_ICON_MAP[pollen]
        self._attr_translation_key = f"pollen_{pollen.value}"
        self._attr_unique_id = f"{entry.data[CONF_UNIQUE_ID]}_pollen_{pollen.value}"
        self._pollen = pollen

    @property
    def native_value(self) -> str | None:
        """Return the pollen level."""
        level = self.coordinator.data.pollen.get(self._pollen)
        return level.value if level is not None else None


class IrmKmiCurrentRainfallSensor(IrmKmiBaseEntity, SensorEntity):
    """Representation of the current rainfall sensor."""

    _attr_icon = "mdi:weather-pouring"
    _attr_translation_key = "current_rainfall"

    def __init__(self, entry: IrmKmiConfigEntry) -> None:
        """Initialize the current rainfall sensor."""
        super().__init__(entry)
        self._attr_unique_id = f"{entry.data[CONF_UNIQUE_ID]}_current_rainfall"

    def _current_forecast(self) -> RadarForecast | None:
        """Return the latest radar forecast that is not in the future."""
        forecasts = self.coordinator.data.radar_forecast
        if not forecasts:
            return None

        now = dt_util.now()
        previous_forecast = forecasts[0]

        for forecast in forecasts:
            if datetime.fromisoformat(forecast["datetime"]) > now:
                return previous_forecast
            previous_forecast = forecast

        return forecasts[-1]

    @property
    def native_value(self) -> float | None:
        """Return the current rainfall."""
        forecast = self._current_forecast()

        if forecast is None:
            return None

        return forecast.get("native_precipitation")

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the current rainfall unit."""
        forecast = self._current_forecast()

        if forecast is None:
            return None

        return forecast.get("unit")


class IrmKmiNextWarningSensor(IrmKmiBaseEntity, SensorEntity):
    """Representation of the next IRM KMI weather warning."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_warning"

    def __init__(self, entry: IrmKmiConfigEntry) -> None:
        """Initialize the next warning sensor."""
        super().__init__(entry)
        self._attr_unique_id = f"{entry.data[CONF_UNIQUE_ID]}_next_warning"

    @property
    def native_value(self) -> datetime | None:
        """Return the start time of the next warning."""
        now = dt_util.now()
        return min(
            (
                warning["starts_at"]
                for warning in self.coordinator.data.warnings
                if now < warning["starts_at"]
            ),
            default=None,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes related to future warnings."""
        now = dt_util.now()
        next_warnings = [
            format_warning(warning, now)
            for warning in self.coordinator.data.warnings
            if now < warning["starts_at"]
        ]
        next_warning_names = [
            warning["friendly_name"]
            for warning in next_warnings
            if warning["friendly_name"]
        ]

        return {
            "next_warnings": next_warnings,
            "next_warnings_friendly_names": ", ".join(next_warning_names),
        }
