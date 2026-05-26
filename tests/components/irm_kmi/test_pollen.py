"""Tests for the IRM KMI pollen sensors."""

from unittest.mock import MagicMock

from irm_kmi_api import IrmKmiApiError, PollenLevel, PollenName, PollenParser

from homeassistant.components.irm_kmi.coordinator import IrmKmiCoordinator
from homeassistant.components.irm_kmi.data import ProcessedCoordinatorData
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

POLLEN_OPTIONS = [level.value for level in PollenParser.get_option_values()]


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
    sensor_entries = [entry for entry in entries if entry.domain == "sensor"]

    assert {entry.translation_key for entry in sensor_entries} == {
        f"pollen_{pollen.value}" for pollen in PollenName
    }
    assert {entry.unique_id for entry in sensor_entries} == {
        f"city country_pollen_{pollen.value}" for pollen in PollenName
    }


async def test_pollen_error_keeps_existing_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
) -> None:
    """Test previous pollen data is kept when refreshing pollen fails."""
    previous_pollen = {
        **PollenParser.get_unavailable_data(),
        PollenName.ALDER: PollenLevel.RED,
    }
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, mock_irm_kmi_api)
    coordinator.data = ProcessedCoordinatorData(
        current_weather={},
        country="BE",
        pollen=previous_pollen,
    )
    mock_irm_kmi_api.get_pollen.side_effect = IrmKmiApiError("Pollen failed")

    result = await coordinator.process_api_data()

    assert result.pollen == previous_pollen


async def test_pollen_error_leads_to_unavailable_on_first_refresh(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
) -> None:
    """Test unavailable pollen data is used when refreshing pollen fails initially."""
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, mock_irm_kmi_api)
    mock_irm_kmi_api.get_pollen.side_effect = IrmKmiApiError("Pollen failed")

    result = await coordinator.process_api_data()

    assert result.pollen == PollenParser.get_unavailable_data()
