"""Service interval sensors for DroneMobile."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength

from .const import UNITS_METRIC
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity


def _slugify_name(name: str) -> str:
    """Convert a service name to a slug key."""
    return name.lower().replace(" ", "_").replace("-", "_")


class ServiceIntervalSensor(DroneMobileEntity, SensorEntity):
    """Sensor showing miles/km remaining until a service is due."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:wrench-clock"

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        interval: dict[str, Any],
        units: str,
    ) -> None:
        """Initialize the service interval sensor."""
        self._interval_name = interval["name"]
        self._interval_miles = interval["interval_miles"]
        self._last_serviced_mileage = interval["last_serviced_mileage"]
        self._units = units
        slug = _slugify_name(self._interval_name)
        super().__init__(coordinator, f"service_{slug}")
        self._attr_name = f"{self._interval_name} Remaining"

    @property
    def native_value(self) -> float | None:
        """Return miles or km remaining until service is due."""
        status = self.coordinator.data.get("status", {})
        odometer = status.get("odometer")
        if odometer is None:
            return None

        miles_remaining = (
            self._last_serviced_mileage + self._interval_miles - float(odometer)
        )

        if self._units == UNITS_METRIC:
            return round(miles_remaining * 1.60934, 1)
        return round(miles_remaining, 1)

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit."""
        if self._units == UNITS_METRIC:
            return UnitOfLength.KILOMETERS
        return UnitOfLength.MILES

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs: dict[str, Any] = {
            "service_name": self._interval_name,
            "interval_miles": self._interval_miles,
            "last_serviced_mileage": self._last_serviced_mileage,
        }
        value = self.native_value
        if value is not None:
            attrs["overdue"] = value < 0
        return attrs
