"""Support for IRM KMI pollen sensors."""

from irm_kmi_api import PollenName, PollenParser

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import POLLEN_TO_ICON_MAP
from .coordinator import IrmKmiConfigEntry
from .entity import IrmKmiBaseEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: IrmKmiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""

    # Set up pollen sensors
    async_add_entities([IrmKmiPollenSensor(entry, pollen) for pollen in PollenName])


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
