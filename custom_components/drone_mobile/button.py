"""Button platform for DroneMobile — mark service as completed."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SERVICE_INTERVALS, DOMAIN
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity
from .service_sensor import _slugify_name

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DroneMobile service interval reset buttons."""
    coordinator: DroneMobileCoordinator = hass.data[DOMAIN][entry.entry_id]
    intervals: list[dict[str, Any]] = entry.options.get(CONF_SERVICE_INTERVALS, [])

    entities = [
        ServiceResetButton(coordinator, entry, interval)
        for interval in intervals
    ]
    if entities:
        async_add_entities(entities)


class ServiceResetButton(DroneMobileEntity, ButtonEntity):
    """Button to mark a service interval as just completed."""

    _attr_icon = "mdi:wrench-check"

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        entry: ConfigEntry,
        interval: dict[str, Any],
    ) -> None:
        """Initialize the button."""
        self._entry = entry
        self._interval_name = interval["name"]
        slug = _slugify_name(self._interval_name)
        super().__init__(coordinator, f"service_reset_{slug}")
        self._attr_name = f"Mark {self._interval_name} Serviced"

    async def async_press(self) -> None:
        """Handle the button press — reset the last_serviced_mileage to current odometer."""
        status = self.coordinator.data.get("status", {})
        odometer = status.get("odometer")
        if odometer is None:
            _LOGGER.warning(
                "Cannot reset service '%s': odometer data unavailable",
                self._interval_name,
            )
            return

        current_mileage = float(odometer)
        intervals: list[dict[str, Any]] = list(
            self._entry.options.get(CONF_SERVICE_INTERVALS, [])
        )

        for interval in intervals:
            if interval["name"] == self._interval_name:
                interval["last_serviced_mileage"] = int(current_mileage)
                break

        new_options = dict(self._entry.options)
        new_options[CONF_SERVICE_INTERVALS] = intervals

        self.hass.config_entries.async_update_entry(
            self._entry, options=new_options
        )
        _LOGGER.info(
            "Service '%s' marked as serviced at %d miles",
            self._interval_name,
            int(current_mileage),
        )
