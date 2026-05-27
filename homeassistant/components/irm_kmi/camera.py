"""Support for the IRM KMI radar camera."""

from aiohttp import web

from homeassistant.components.camera import Camera, async_get_still_stream
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import IrmKmiConfigEntry
from .entity import IrmKmiBaseEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: IrmKmiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the camera platform."""
    async_add_entities([IrmKmiRadarCamera(entry)])


class IrmKmiRadarCamera(IrmKmiBaseEntity, Camera):
    """Representation of the IRM KMI radar camera."""

    _attr_frame_interval = 1
    _attr_translation_key = "radar"

    def __init__(self, entry: IrmKmiConfigEntry) -> None:
        """Initialize the radar camera."""
        IrmKmiBaseEntity.__init__(self, entry)
        Camera.__init__(self)
        self.content_type = "image/svg+xml"
        self._attr_unique_id = f"{entry.data[CONF_UNIQUE_ID]}_radar"
        self._image_index = False

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return the radar still image."""
        if self.coordinator.data.animation is None:
            return None

        return await self.coordinator.data.animation.get_still()

    async def handle_async_still_stream(
        self, request: web.Request, interval: float
    ) -> web.StreamResponse:
        """Generate an HTTP MJPEG stream from camera images."""
        self._image_index = False
        return await async_get_still_stream(
            request, self.get_animated_svg, self.content_type, interval
        )

    async def handle_async_mjpeg_stream(
        self, request: web.Request
    ) -> web.StreamResponse:
        """Serve an HTTP MJPEG stream from the camera."""
        return await self.handle_async_still_stream(request, self.frame_interval)

    async def get_animated_svg(self) -> bytes | None:
        """Return the animated SVG for camera display."""
        # If this is not done this way, the live view can only be opened once
        self._image_index = not self._image_index

        if not self._image_index or self.coordinator.data.animation is None:
            return None

        return await self.coordinator.data.animation.get_animated()

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return the camera state attributes."""
        animation = self.coordinator.data.animation
        return {"hint": animation.get_hint() if animation is not None else None}
