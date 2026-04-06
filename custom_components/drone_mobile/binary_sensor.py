"""Binary sensor platform for DroneMobile."""
from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SERVICE_INTERVALS,
    DOMAIN,
    INTERVAL_TYPE_MILEAGE,
    INTERVAL_TYPE_TIME,
    TIME_PERIOD_MONTHS,
)
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity
from .service_sensor import _compute_due_date, _slugify_name

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
    entities: list[BinarySensorEntity] = [
        DroneMobileBinarySensor(coordinator, desc)
        for desc in BINARY_SENSOR_DESCRIPTIONS
    ]

    intervals: list[dict[str, Any]] = entry.options.get(CONF_SERVICE_INTERVALS, [])
    for interval in intervals:
        entities.append(ServiceIntervalOverdueBinarySensor(coordinator, entry, interval))

    async_add_entities(entities)


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


class ServiceIntervalOverdueBinarySensor(DroneMobileEntity, BinarySensorEntity):
    """Binary sensor that turns on when a maintenance interval is overdue."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:wrench-clock"

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        entry: Any,
        interval: dict[str, Any],
    ) -> None:
        """Initialize the service interval overdue binary sensor."""
        self._entry = entry
        self._interval_name = interval["name"]
        self._interval_type = interval.get("type", INTERVAL_TYPE_MILEAGE)

        slug = _slugify_name(self._interval_name)
        super().__init__(coordinator, f"service_{slug}_overdue")
        self._attr_name = f"{self._interval_name} Overdue"

    def _get_live_interval(self) -> dict[str, Any] | None:
        """Re-read this interval from the live config entry options."""
        intervals = self._entry.options.get(CONF_SERVICE_INTERVALS, [])
        for iv in intervals:
            if iv.get("name") == self._interval_name:
                return iv
        return None

    def _mileage_remaining(self, iv: dict[str, Any]) -> float | None:
        """Compute miles remaining for mileage-based intervals."""
        status = self.coordinator.data.get("status", {})
        odometer = status.get("odometer")
        if odometer is None:
            return None

        interval_miles = iv.get("interval_miles", 0)
        last_serviced = iv.get("last_serviced_mileage", 0)
        miles_remaining = last_serviced + interval_miles - float(odometer)
        return min(miles_remaining, float(interval_miles))

    def _time_remaining(self, iv: dict[str, Any]) -> int | None:
        """Compute days remaining for time-based intervals."""
        due = _compute_due_date(
            {
                "last_serviced_date": iv.get("last_serviced_date", ""),
                "period": iv.get("period", TIME_PERIOD_MONTHS),
                "interval_value": iv.get("interval_value", 0),
            }
        )
        if due is None:
            return None
        return (due - date.today()).days

    @property
    def is_on(self) -> bool | None:
        """Return true when the service interval is overdue."""
        iv = self._get_live_interval()
        if iv is None:
            return None

        if self._interval_type == INTERVAL_TYPE_TIME:
            days_remaining = self._time_remaining(iv)
            if days_remaining is None:
                return None
            return days_remaining < 0

        miles_remaining = self._mileage_remaining(iv)
        if miles_remaining is None:
            return None
        return miles_remaining < 0
