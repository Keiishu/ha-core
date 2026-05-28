"""Config flow to set up IRM KMI integration via the UI."""

from collections.abc import Mapping
import logging
from typing import Any

from irm_kmi_api import IrmKmiApiClient, IrmKmiApiError, RadarStyle
import voluptuous as vol

from homeassistant.components.zone import DOMAIN as ZONE_DOMAIN
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.const import (
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    CONF_LOCATION,
    CONF_UNIQUE_ID,
    CONF_ZONE,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    LocationSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_LANGUAGE_OVERRIDE,
    CONF_LANGUAGE_OVERRIDE_OPTIONS,
    CONF_RADAR_DARK_MODE,
    CONF_RADAR_STYLE,
    DEFAULT_RADAR_DARK_MODE,
    DEFAULT_RADAR_STYLE,
    DOMAIN,
    OUT_OF_BENELUX,
    USER_AGENT,
)
from .coordinator import IrmKmiConfigEntry

_LOGGER = logging.getLogger(__name__)

ZONE_HOME = "zone.home"


class IrmKmiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuration flow for the IRM KMI integration."""

    VERSION = 1
    _location: dict[str, float] | None = None
    _title: str | None = None
    _unique_id: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(_config_entry: IrmKmiConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return IrmKmiOptionFlow()

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Define the user step of the configuration flow."""
        errors: dict = {}

        if user_input:
            _LOGGER.debug("Provided config user is: %s", user_input)

            zone = self.hass.states.get(user_input[CONF_ZONE])
            if zone is None:
                errors[CONF_ZONE] = "zone_not_found"
            else:
                self._location = {
                    ATTR_LATITUDE: zone.attributes[ATTR_LATITUDE],
                    ATTR_LONGITUDE: zone.attributes[ATTR_LONGITUDE],
                }
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ZONE, default=ZONE_HOME): EntitySelector(
                        EntitySelectorConfig(domain=ZONE_DOMAIN)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Confirm the location to use for weather data."""
        errors: dict = {}

        default_location = self._location or {
            ATTR_LATITUDE: self.hass.config.latitude,
            ATTR_LONGITUDE: self.hass.config.longitude,
        }

        if user_input:
            _LOGGER.debug("Provided config user is: %s", user_input)
            location = user_input[CONF_LOCATION]
            lat: float = location[ATTR_LATITUDE]
            lon: float = location[ATTR_LONGITUDE]

            try:
                api_data = await IrmKmiApiClient(
                    session=async_get_clientsession(self.hass),
                    user_agent=USER_AGENT,
                ).get_forecasts_coord({"lat": lat, "long": lon})
            except IrmKmiApiError:
                _LOGGER.exception(
                    "Encountered an unexpected error while configuring the integration"
                )
                return self.async_abort(reason="api_error")

            if api_data["cityName"] in OUT_OF_BENELUX:
                errors[CONF_LOCATION] = "out_of_benelux"

            if not errors:
                name: str = api_data["cityName"]
                country: str = api_data["country"]
                unique_id: str = f"{name.lower()} {country.lower()}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                self._location = location
                self._title = name
                self._unique_id = unique_id

                return await self.async_step_radar()

            default_location = location

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOCATION, default=default_location
                    ): LocationSelector()
                }
            ),
            errors=errors,
        )

    async def async_step_radar(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Configure radar options."""
        if user_input is not None:
            _LOGGER.debug("Provided config user is: %s", user_input)

            return self.async_create_entry(
                title=self._title or "IRM KMI",
                data={
                    CONF_LOCATION: self._location,
                    CONF_UNIQUE_ID: self._unique_id,
                },
                options={
                    CONF_RADAR_DARK_MODE: user_input.get(
                        CONF_RADAR_DARK_MODE, DEFAULT_RADAR_DARK_MODE
                    ),
                    CONF_RADAR_STYLE: user_input.get(
                        CONF_RADAR_STYLE, DEFAULT_RADAR_STYLE
                    ),
                },
            )

        return self.async_show_form(
            step_id="radar",
            data_schema=vol.Schema(_radar_options_schema({})),
        )


class IrmKmiOptionFlow(OptionsFlowWithReload):
    """Option flow for the IRM KMI integration.

    Helps change options once the integration was configured.
    """

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.debug("Provided config user is: %s", user_input)
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(_options_schema(self.config_entry.options)),
        )


def _radar_options_schema(options: Mapping[str, Any]) -> dict:
    """Return the schema fields for radar options."""
    return {
        vol.Optional(
            CONF_RADAR_STYLE,
            default=options.get(CONF_RADAR_STYLE, DEFAULT_RADAR_STYLE),
        ): SelectSelector(
            SelectSelectorConfig(
                options=[style.value for style in RadarStyle],
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_RADAR_STYLE,
            )
        ),
        vol.Optional(
            CONF_RADAR_DARK_MODE,
            default=options.get(CONF_RADAR_DARK_MODE, DEFAULT_RADAR_DARK_MODE),
        ): bool,
    }


def _options_schema(options: Mapping[str, Any]) -> dict:
    """Return the schema fields for integration options."""
    return {
        **_radar_options_schema(options),
        vol.Optional(
            CONF_LANGUAGE_OVERRIDE,
            default=options.get(CONF_LANGUAGE_OVERRIDE, "none"),
        ): SelectSelector(
            SelectSelectorConfig(
                options=CONF_LANGUAGE_OVERRIDE_OPTIONS,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=CONF_LANGUAGE_OVERRIDE,
            )
        ),
    }
