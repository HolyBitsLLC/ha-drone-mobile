"""Binary sensor platform for DroneMobile."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity

BINARY_SENSOR_DESCRIPTIONS: list[BinarySensorEntityDescription] = [
    BinarySensorEntityDescription(
        key="is_running",
        name="Engine",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:engine",
    ),
    BinarySensorEntityDescription(
        key="is_locked",
        name="Locked",
        device_class=BinarySensorDeviceClass.LOCK,
        icon="mdi:car-door-lock",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DroneMobile binary sensors."""
    coordinator: DroneMobileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DroneMobileBinarySensor(coordinator, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class DroneMobileBinarySensor(DroneMobileEntity, BinarySensorEntity):
    """Representation of a DroneMobile binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        status = self.coordinator.data.get("status", {})
        value = status.get(self.entity_description.key)
        if value is None:
            return None
        # For 'is_locked', BinarySensorDeviceClass.LOCK semantics:
        # is_on=True means "unlocked" (problem state)
        if self.entity_description.key == "is_locked":
            return not value
        return value
