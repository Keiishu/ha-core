"""Tests for the IRM KMI pollen sensors."""

from unittest.mock import MagicMock

from irm_kmi_api import PollenLevel, PollenName

from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from tests.common import MockConfigEntry

POLLEN_DATA = {
    PollenName.ALDER: PollenLevel.GREEN,
    PollenName.ASH: PollenLevel.YELLOW,
    PollenName.BIRCH: PollenLevel.ORANGE,
    PollenName.GRASSES: PollenLevel.RED,
    PollenName.HAZEL: PollenLevel.PURPLE,
    PollenName.MUGWORT: PollenLevel.ACTIVE,
    PollenName.OAK: PollenLevel.NONE,
}


async def test_pollen_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test pollen sensors are created, with correct names."""
    mock_irm_kmi_api.get_pollen.return_value = POLLEN_DATA
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    pollen_translation_keys = {f"pollen_{pollen.value}" for pollen in PollenName}
    pollen_sensor_entries = [
        entry
        for entry in entries
        if entry.domain == "sensor" and entry.translation_key in pollen_translation_keys
    ]

    assert {
        entry.translation_key for entry in pollen_sensor_entries
    } == pollen_translation_keys
    assert {entry.unique_id for entry in pollen_sensor_entries} == {
        f"city country_pollen_{pollen.value}" for pollen in PollenName
    }
