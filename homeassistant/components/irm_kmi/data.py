"""Define data classes for the IRM KMI integration."""

from dataclasses import dataclass, field

from irm_kmi_api import (
    CurrentWeatherData,
    ExtendedForecast,
    PollenLevel,
    PollenName,
    RadarForecast,
    RainGraph,
    WarningData,
)

from homeassistant.components.weather import Forecast


@dataclass
class ProcessedCoordinatorData:
    """Data exposed to entities consuming IrmKmiCoordinator data."""

    current_weather: CurrentWeatherData
    country: str
    animation: RainGraph | None = None
    pollen: dict[PollenName, PollenLevel | None] = field(default_factory=dict)
    warnings: list[WarningData] = field(default_factory=list)
    hourly_forecast: list[Forecast] = field(default_factory=list)
    daily_forecast: list[ExtendedForecast] = field(default_factory=list)
    radar_forecast: list[RadarForecast] = field(default_factory=list)
