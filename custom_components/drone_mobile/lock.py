"""Lock platform for DroneMobile."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_LOCK, CMD_UNLOCK, DOMAIN
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DroneMobile lock."""
    coordinator: DroneMobileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DroneMobileLock(coordinator)])


class DroneMobileLock(DroneMobileEntity, LockEntity):
    """Representation of the vehicle door lock."""

    _attr_name = "Door Lock"

    def __init__(self, coordinator: DroneMobileCoordinator) -> None:
        """Initialize the lock."""
        super().__init__(coordinator, "door_lock")

    @property
    def is_locked(self) -> bool | None:
        """Return true if the vehicle is locked."""
        status = self.coordinator.data.get("status", {})
        return status.get("is_locked")

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the vehicle."""
        _LOGGER.debug("Locking %s", self.coordinator.data["name"])
        await self.coordinator.async_send_command(CMD_LOCK)

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the vehicle."""
        _LOGGER.debug("Unlocking %s", self.coordinator.data["name"])
        await self.coordinator.async_send_command(CMD_UNLOCK)
