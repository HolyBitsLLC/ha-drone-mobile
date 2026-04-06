"""Device tracker platform for DroneMobile."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DroneMobile device tracker."""
    coordinator: DroneMobileCoordinator = hass.data[DOMAIN][entry.entry_id]
    # Only add tracker if GPS data is available
    if coordinator.data.get("location"):
        async_add_entities([DroneMobileTracker(coordinator)])


class DroneMobileTracker(DroneMobileEntity, TrackerEntity):
    """Representation of the vehicle GPS tracker."""

    _attr_name = "Location"
    _attr_icon = "mdi:car-connected"

    def __init__(self, coordinator: DroneMobileCoordinator) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator, "tracker")

    @property
    def latitude(self) -> float | None:
        """Return the latitude."""
        location = self.coordinator.data.get("location")
        if location:
            return location.get("latitude")
        return None

    @property
    def longitude(self) -> float | None:
        """Return the longitude."""
        location = self.coordinator.data.get("location")
        if location:
            return location.get("longitude")
        return None

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GPS
