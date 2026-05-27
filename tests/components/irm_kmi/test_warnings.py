"""Tests for the IRM KMI warning entities."""

import json
from unittest.mock import MagicMock

from irm_kmi_api import IrmKmiApiClientHa, WarningData
import pytest

from homeassistant.components.irm_kmi.const import CONF_LANGUAGE_OVERRIDE, DOMAIN
from homeassistant.const import STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from tests.common import MockConfigEntry, load_fixture


def _warnings_from_fixture(lang: str) -> list[WarningData]:
    """Return parsed warning data from the warning fixture."""
    api_client = IrmKmiApiClientHa(session=MagicMock(), user_agent="")
    api_client._api_data = json.loads(load_fixture("warnings.json", "irm_kmi"))
    return api_client.get_warnings(lang)


async def _setup_warning_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
    warning_data: list[WarningData],
) -> tuple[str, str]:
    """Set up the integration and return warning entity IDs."""
    mock_irm_kmi_api.get_warnings.return_value = list(warning_data)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    warning_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, "city country_warning"
    )
    next_warning_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "city country_next_warning"
    )

    assert warning_entity_id is not None
    assert next_warning_entity_id is not None

    return warning_entity_id, next_warning_entity_id


@pytest.mark.freeze_time("2026-01-12T07:55:00+01:00")
async def test_warning_binary_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the warning binary sensor shows active warnings."""
    warning_entity_id, _ = await _setup_warning_entities(
        hass,
        mock_config_entry,
        mock_irm_kmi_api,
        entity_registry,
        _warnings_from_fixture("en"),
    )

    state = hass.states.get(warning_entity_id)

    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["active_warnings_friendly_names"] == "Fog, Ice or snow"
    assert state.attributes["warnings"][0]["is_active"]
    assert state.attributes["warnings"][1]["is_active"]


@pytest.mark.freeze_time("2026-01-11T20:00:00+01:00")
async def test_next_warning_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the next warning sensor shows the earliest future warning."""
    _, next_warning_entity_id = await _setup_warning_entities(
        hass,
        mock_config_entry,
        mock_irm_kmi_api,
        entity_registry,
        _warnings_from_fixture("en"),
    )

    state = hass.states.get(next_warning_entity_id)

    assert state is not None
    assert state.state == "2026-01-12T06:00:00+00:00"
    assert state.attributes["next_warnings_friendly_names"] == "Fog, Ice or snow"
    assert len(state.attributes["next_warnings"]) == 2
    mock_irm_kmi_api.get_warnings.assert_called_once_with("en")


@pytest.mark.freeze_time("2026-01-11T20:00:00+01:00")
async def test_warnings_use_language_override(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test warnings use the configured language override."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_LANGUAGE_OVERRIDE: "de"}
    )

    mock_irm_kmi_api.get_warnings.return_value = _warnings_from_fixture("de")

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    next_warning_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, "city country_next_warning"
    )
    assert next_warning_entity_id is not None

    state = hass.states.get(next_warning_entity_id)

    assert state is not None
    assert state.attributes["next_warnings_friendly_names"] == "Nebel, Glätte"
    mock_irm_kmi_api.get_warnings.assert_called_once_with("de")


@pytest.mark.freeze_time("2026-01-12T07:55:00+01:00")
async def test_next_warning_sensor_unknown_when_only_active_warnings(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test active warnings are not exposed as next warnings."""
    _, next_warning_entity_id = await _setup_warning_entities(
        hass,
        mock_config_entry,
        mock_irm_kmi_api,
        entity_registry,
        _warnings_from_fixture("en"),
    )

    state = hass.states.get(next_warning_entity_id)

    assert state is not None
    assert state.state == STATE_UNKNOWN
    assert state.attributes["next_warnings_friendly_names"] == ""
    assert state.attributes["next_warnings"] == []
