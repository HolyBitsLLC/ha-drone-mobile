"""Button platform for DroneMobile — mark service as completed."""
from __future__ import annotations

import copy
import logging
from datetime import date
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_SERVICE_INTERVALS, DOMAIN, INTERVAL_TYPE_MILEAGE, INTERVAL_TYPE_TIME
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
        self._interval_type = interval.get("type", INTERVAL_TYPE_MILEAGE)
        slug = _slugify_name(self._interval_name)
        super().__init__(coordinator, f"service_reset_{slug}")
        self._attr_name = f"Mark {self._interval_name} Serviced"

    async def async_press(self) -> None:
        """Handle the button press — reset the interval to current odometer/date."""
        intervals: list[dict[str, Any]] = copy.deepcopy(
            list(self._entry.options.get(CONF_SERVICE_INTERVALS, []))
        )

        if self._interval_type == INTERVAL_TYPE_TIME:
            today_str = date.today().isoformat()
            for interval in intervals:
                if interval["name"] == self._interval_name:
                    interval["last_serviced_date"] = today_str
                    break
            _LOGGER.info(
                "Service '%s' marked as serviced on %s",
                self._interval_name,
                today_str,
            )
        else:
            status = self.coordinator.data.get("status", {})
            odometer = status.get("odometer")
            if odometer is None:
                _LOGGER.warning(
                    "Cannot reset service '%s': odometer data unavailable",
                    self._interval_name,
                )
                return

            current_mileage = int(float(odometer))
            for interval in intervals:
                if interval["name"] == self._interval_name:
                    interval["last_serviced_mileage"] = current_mileage
                    break
            _LOGGER.info(
                "Service '%s' marked as serviced at %d miles",
                self._interval_name,
                current_mileage,
            )

        new_options = dict(self._entry.options)
        new_options[CONF_SERVICE_INTERVALS] = intervals

        self.hass.config_entries.async_update_entry(
            self._entry, options=new_options
        )

        # Force all entities to pick up the new options immediately
        await self.coordinator.async_request_refresh()
