"""Tests for IRM KMI radar forecasts."""

import json
from unittest.mock import MagicMock

from irm_kmi_api import IrmKmiApiClientHa, RadarForecast
import pytest

from homeassistant.components.irm_kmi.const import (
    ATTR_INCLUDE_PAST_FORECASTS,
    DOMAIN,
    SERVICE_GET_FORECASTS_RADAR,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_UNIT_OF_MEASUREMENT, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from tests.common import MockConfigEntry, load_fixture


def _radar_forecasts_from_fixture() -> list[RadarForecast]:
    """Return parsed radar forecast data from the forecast fixture."""
    api_client = IrmKmiApiClientHa(session=MagicMock(), user_agent="")
    api_client._api_data = json.loads(load_fixture("forecast.json", "irm_kmi"))
    return api_client.get_radar_forecast()


async def _setup_radar_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    radar_forecasts: list[RadarForecast],
) -> None:
    """Set up the integration with the provided radar forecasts."""
    mock_irm_kmi_api.get_radar_forecast.return_value = list(radar_forecasts)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time("2023-12-26T17:58:03+01:00")
@pytest.mark.parametrize(
    ("include_past_forecasts", "expected_forecast_index"),
    [
        pytest.param(False, 5, id="current-and-future"),
        pytest.param(True, 0, id="with-past"),
    ],
)
async def test_radar_forecast_service(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    include_past_forecasts: bool,
    expected_forecast_index: int,
) -> None:
    """Test the radar forecast service."""
    radar_forecasts = _radar_forecasts_from_fixture()
    await _setup_radar_entities(
        hass, mock_config_entry, mock_irm_kmi_api, radar_forecasts
    )

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_FORECASTS_RADAR,
        {
            ATTR_ENTITY_ID: "weather.home",
            ATTR_INCLUDE_PAST_FORECASTS: include_past_forecasts,
        },
        blocking=True,
        return_response=True,
    )

    assert response == {
        "weather.home": {"forecast": radar_forecasts[expected_forecast_index:]}
    }


@pytest.mark.freeze_time("2023-12-26T17:58:03+01:00")
async def test_current_rainfall_sensor_uses_latest_radar_forecast_not_future(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the current rainfall sensor uses the latest radar forecast in the past."""
    radar_forecasts = _radar_forecasts_from_fixture()
    await _setup_radar_entities(
        hass, mock_config_entry, mock_irm_kmi_api, radar_forecasts
    )

    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "city country_current_rainfall"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)

    assert state is not None
    assert state.state == "0.01"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "mm/10min"


async def test_current_rainfall_sensor_unknown_without_radar_forecast(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the current rainfall sensor is unknown without radar forecasts."""
    await _setup_radar_entities(hass, mock_config_entry, mock_irm_kmi_api, [])

    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "city country_current_rainfall"
    )
    assert entity_id is not None

    state = hass.states.get(entity_id)

    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert ATTR_UNIT_OF_MEASUREMENT not in state.attributes
