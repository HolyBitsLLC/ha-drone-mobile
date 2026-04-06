"""Switch platform for DroneMobile."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_AUX1,
    CMD_AUX2,
    CMD_PANIC_OFF,
    CMD_PANIC_ON,
    CMD_START,
    CMD_STOP,
    CMD_TRUNK,
    DOMAIN,
)
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity

_LOGGER = logging.getLogger(__name__)

SWITCH_DESCRIPTIONS: list[SwitchEntityDescription] = [
    SwitchEntityDescription(
        key="remote_start",
        name="Remote Start",
        icon="mdi:car-key",
    ),
    SwitchEntityDescription(
        key="panic",
        name="Panic",
        icon="mdi:alarm-light",
    ),
    SwitchEntityDescription(
        key="trunk",
        name="Trunk",
        icon="mdi:car-back",
    ),
    SwitchEntityDescription(
        key="aux1",
        name="Auxiliary 1",
        icon="mdi:numeric-1-box",
    ),
    SwitchEntityDescription(
        key="aux2",
        name="Auxiliary 2",
        icon="mdi:numeric-2-box",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DroneMobile switches."""
    coordinator: DroneMobileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DroneMobileSwitch(coordinator, desc) for desc in SWITCH_DESCRIPTIONS
    )


class DroneMobileSwitch(DroneMobileEntity, SwitchEntity):
    """Representation of a DroneMobile command switch."""

    entity_description: SwitchEntityDescription

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        status = self.coordinator.data.get("status", {})
        key = self.entity_description.key
        if key == "remote_start":
            return status.get("is_running")
        # Aux/trunk/panic are momentary — always show off
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        key = self.entity_description.key
        _LOGGER.debug("Turning on %s for %s", key, self.coordinator.data["name"])
        cmd_map = {
            "remote_start": CMD_START,
            "panic": CMD_PANIC_ON,
            "trunk": CMD_TRUNK,
            "aux1": CMD_AUX1,
            "aux2": CMD_AUX2,
        }
        cmd = cmd_map.get(key)
        if cmd:
            await self.coordinator.async_send_command(cmd)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        key = self.entity_description.key
        _LOGGER.debug("Turning off %s for %s", key, self.coordinator.data["name"])
        cmd_map = {
            "remote_start": CMD_STOP,
            "panic": CMD_PANIC_OFF,
        }
        cmd = cmd_map.get(key)
        if cmd:
            await self.coordinator.async_send_command(cmd)
