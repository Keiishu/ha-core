"""Test for the weather entity of the IRM KMI integration."""

from unittest.mock import AsyncMock, MagicMock, patch

from irm_kmi_api import ExtendedForecast
import pytest
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.irm_kmi.coordinator import IrmKmiCoordinator
from homeassistant.components.irm_kmi.data import ProcessedCoordinatorData
from homeassistant.components.irm_kmi.weather import IrmKmiWeather
from homeassistant.components.weather import (
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform


def _create_weather_with_daily_forecast(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    daily_forecast: list[ExtendedForecast] | None,
) -> IrmKmiWeather:
    """Create the weather entity with the provided daily forecast data."""
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, MagicMock())
    coordinator.data = ProcessedCoordinatorData(
        current_weather={},
        country="BE",
        daily_forecast=daily_forecast,
    )
    mock_config_entry.runtime_data = coordinator
    return IrmKmiWeather(mock_config_entry)


@pytest.mark.freeze_time("2023-12-28T15:30:00+01:00")
async def test_weather_nl(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api_nl: AsyncMock,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test weather with forecast from the Netherland."""
    mock_config_entry.add_to_hass(hass)

    with patch("homeassistant.components.irm_kmi.PLATFORMS", [Platform.WEATHER]):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_daily_forecast_uses_night_first_low_temperature(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test daily forecast uses the night first low temperature."""
    night_forecast: ExtendedForecast = {
        "datetime": "2026-01-21T00:00:00+01:00",
        "is_daytime": False,
        "native_templow": 8,
        "native_temperature": 8,
    }
    day_forecast: ExtendedForecast = {
        "datetime": "2026-01-21T12:00:00+01:00",
        "is_daytime": True,
        "native_templow": None,
        "native_temperature": 7,
    }

    weather = _create_weather_with_daily_forecast(
        hass,
        mock_config_entry,
        [night_forecast, day_forecast],
    )

    assert weather.daily_forecast() == [
        {
            "datetime": "2026-01-21T00:00:00+01:00",
            "is_daytime": False,
            "native_templow": 8,
            "native_temperature": 8,
        },
        {
            "datetime": "2026-01-21T12:00:00+01:00",
            "is_daytime": True,
            "native_templow": 7,
            "native_temperature": 8,
        },
    ]


@pytest.mark.parametrize(
    "forecast_type",
    ["daily", "hourly"],
)
@pytest.mark.freeze_time("2025-09-22T15:30:00+01:00")
async def test_forecast_service(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    mock_irm_kmi_api_nl: AsyncMock,
    mock_config_entry: MockConfigEntry,
    forecast_type: str,
) -> None:
    """Test multiple forecast."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    response = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {
            ATTR_ENTITY_ID: "weather.home",
            "type": forecast_type,
        },
        blocking=True,
        return_response=True,
    )
    assert response == snapshot


@pytest.mark.freeze_time("2024-01-21T14:15:00+01:00")
@pytest.mark.parametrize(
    "forecast_type",
    ["daily", "hourly"],
)
async def test_weather_higher_temp_at_night(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api_high_low_temp: AsyncMock,
    forecast_type: str,
) -> None:
    """Test templow is always lower than temperature."""
    # Test case for https://github.com/jdejaegh/irm-kmi-ha/issues/8
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    response = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {
            ATTR_ENTITY_ID: "weather.home",
            "type": forecast_type,
        },
        blocking=True,
        return_response=True,
    )
    for forecast in response["weather.home"]["forecast"]:
        assert (
            forecast.get("native_temperature") is None
            or forecast.get("native_templow") is None
            or forecast["native_temperature"] >= forecast["native_templow"]
        )
