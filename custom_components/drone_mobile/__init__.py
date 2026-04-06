"""The DroneMobile integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SERVICE_INTERVALS, DOMAIN, INTERVAL_TYPE_MILEAGE
from .coordinator import DroneMobileCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]


def _migrate_service_intervals(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Backfill 'type' field on legacy service intervals (pre-v1.2.0).

    Service interval data lives in config_entry.options, which persists
    in .storage/core.config_entries across HACS updates. This migration
    ensures intervals created before the type field was added still work.
    """
    intervals = entry.options.get(CONF_SERVICE_INTERVALS, [])
    if not intervals:
        return

    updated = False
    new_intervals = []
    for interval in intervals:
        interval = dict(interval)  # don't mutate the original
        if "type" not in interval:
            interval["type"] = INTERVAL_TYPE_MILEAGE
            updated = True
        new_intervals.append(interval)

    if updated:
        new_options = dict(entry.options)
        new_options[CONF_SERVICE_INTERVALS] = new_intervals
        hass.config_entries.async_update_entry(entry, options=new_options)
        _LOGGER.info(
            "Migrated %d service intervals to include type field",
            len(new_intervals),
        )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DroneMobile from a config entry."""
    _migrate_service_intervals(hass, entry)

    coordinator = DroneMobileCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update — reload the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
