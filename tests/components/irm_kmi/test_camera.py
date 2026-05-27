"""Tests for the IRM KMI radar camera."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN
from homeassistant.components.irm_kmi.camera import IrmKmiRadarCamera
from homeassistant.components.irm_kmi.const import DOMAIN
from homeassistant.components.irm_kmi.coordinator import IrmKmiCoordinator
from homeassistant.components.irm_kmi.data import ProcessedCoordinatorData
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
import homeassistant.helpers.entity_registry as er

from tests.common import MockConfigEntry


async def test_radar_camera_entity(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_irm_kmi_api: MagicMock,
) -> None:
    """Test the radar camera entity is created."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = entity_registry.async_get_entity_id(
        CAMERA_DOMAIN, DOMAIN, f"{mock_config_entry.data[CONF_UNIQUE_ID]}_radar"
    )

    assert entity_id is not None
    assert hass.states.get(entity_id) is not None


async def test_camera_initialization(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test radar camera initialization."""
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, MagicMock())
    mock_config_entry.runtime_data = coordinator

    camera = IrmKmiRadarCamera(mock_config_entry)

    assert camera.unique_id == f"{mock_config_entry.data[CONF_UNIQUE_ID]}_radar"
    assert camera.content_type == "image/svg+xml"
    assert camera.frame_interval == 1


async def test_radar_camera_image_and_animation(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test radar camera images are returned from the animation data."""
    coordinator = IrmKmiCoordinator(hass, mock_config_entry, MagicMock())
    mock_config_entry.runtime_data = coordinator

    animation = MagicMock()
    animation.get_still = AsyncMock(return_value=b"still")
    animation.get_animated = AsyncMock(return_value=b"animated")

    coordinator.data = ProcessedCoordinatorData(
        current_weather={},
        country="BE",
        animation=animation,
    )
    camera = IrmKmiRadarCamera(mock_config_entry)

    assert await camera.async_camera_image() == b"still"
    assert await camera.get_animated_svg() == b"animated"
    assert await camera.get_animated_svg() is None

    coordinator.data.animation = None

    assert await camera.async_camera_image() is None
    assert await camera.get_animated_svg() is None
