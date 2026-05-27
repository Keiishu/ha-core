"""Tests for the IRM KMI coordinator."""

from datetime import timedelta
import json
from unittest.mock import AsyncMock, MagicMock

from freezegun.api import FrozenDateTimeFactory
from irm_kmi_api import (
    IrmKmiApiClientHa,
    IrmKmiApiError,
    PollenLevel,
    PollenName,
    PollenParser,
)

from homeassistant.components.irm_kmi.const import IRM_KMI_TO_HA_CONDITION_MAP
from homeassistant.components.irm_kmi.coordinator import IrmKmiCoordinator
from homeassistant.components.irm_kmi.data import ProcessedCoordinatorData
from homeassistant.components.weather import ATTR_CONDITION_CLOUDY
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry, async_fire_time_changed, load_fixture


def _api_client_with_fixture(fixture: str) -> IrmKmiApiClientHa:
    """Return an API client loaded with fixture data."""
    api_client = IrmKmiApiClientHa(
        session=MagicMock(),
        user_agent="",
        cdt_map=IRM_KMI_TO_HA_CONDITION_MAP,
    )
    api_client._api_data = json.loads(load_fixture(fixture, "irm_kmi"))
    return api_client


async def test_coordinator_uses_stale_data_before_threshold(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
) -> None:
    """Test stale data is used if update fails before the threshold."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE
    initial_state = state.state

    mock_irm_kmi_api.refresh_forecasts_coord.side_effect = IrmKmiApiError(
        "Connection failed"
    )

    freezer.tick(timedelta(minutes=7, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state is not None
    assert state.state == initial_state


async def test_coordinator_becomes_unavailable_after_repeated_failures(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
) -> None:
    """Test entity becomes unavailable if updates fail past the threshold."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state is not None
    assert state.state != STATE_UNAVAILABLE

    mock_irm_kmi_api.refresh_forecasts_coord.side_effect = IrmKmiApiError(
        "Connection failed"
    )

    for _ in range(3):
        freezer.tick(timedelta(minutes=7, seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    state = hass.states.get("weather.home")
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_refresh_succeeds_even_when_pollen_fails(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test weather data is processed when refreshing pollen fails."""
    api_client = _api_client_with_fixture("forecast.json")
    api_client.get_pollen = AsyncMock(side_effect=IrmKmiApiError("Pollen failed badly"))
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, api_client)

    result = await coordinator.process_api_data()

    assert result.current_weather["condition"] == ATTR_CONDITION_CLOUDY
    assert result.daily_forecast
    assert result.hourly_forecast
    assert result.pollen == PollenParser.get_unavailable_data()


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


async def test_refresh_succeeds_even_when_radar_animation_fails(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test weather data is processed when refreshing radar animation fails."""
    api_client = _api_client_with_fixture("forecast.json")
    api_client.get_animation_data = MagicMock(side_effect=ValueError)
    api_client.get_pollen = AsyncMock(return_value=PollenParser.get_unavailable_data())
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, api_client)

    result = await coordinator.process_api_data()

    assert result.animation is None
    assert result.current_weather["condition"] == ATTR_CONDITION_CLOUDY
