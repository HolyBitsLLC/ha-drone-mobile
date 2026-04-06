"""Service interval sensors for DroneMobile."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfTime

from .const import (
    INTERVAL_TYPE_MILEAGE,
    INTERVAL_TYPE_TIME,
    TIME_PERIOD_MONTHS,
    TIME_PERIOD_WEEKS,
    UNITS_METRIC,
)
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity


def _slugify_name(name: str) -> str:
    """Convert a service name to a slug key."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _add_months(start: date, months: int) -> date:
    """Add N calendar months to a date."""
    month = start.month - 1 + months
    year = start.year + month // 12
    month = month % 12 + 1
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    day = min(start.day, max_day)
    return date(year, month, day)


def _compute_due_date(interval: dict[str, Any]) -> date | None:
    """Compute the due date for a time-based interval."""
    last_str = interval.get("last_serviced_date", "")
    if not last_str:
        return None
    try:
        last = date.fromisoformat(last_str)
    except (ValueError, TypeError):
        return None

    period = interval.get("period", TIME_PERIOD_MONTHS)
    value = interval.get("interval_value", 6)

    if period == TIME_PERIOD_MONTHS:
        return _add_months(last, value)
    if period == TIME_PERIOD_WEEKS:
        return last + timedelta(weeks=value)
    # days
    return last + timedelta(days=value)


class ServiceIntervalSensor(DroneMobileEntity, SensorEntity):
    """Sensor showing miles/km remaining or days remaining until service is due."""

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
        self._interval_type = interval.get("type", INTERVAL_TYPE_MILEAGE)
        self._units = units

        # Mileage fields
        self._interval_miles = interval.get("interval_miles", 0)
        self._last_serviced_mileage = interval.get("last_serviced_mileage", 0)

        # Time fields
        self._interval_value = interval.get("interval_value", 0)
        self._period = interval.get("period", TIME_PERIOD_MONTHS)
        self._recurring = interval.get("recurring", True)
        self._last_serviced_date = interval.get("last_serviced_date", "")

        slug = _slugify_name(self._interval_name)
        super().__init__(coordinator, f"service_{slug}")
        self._attr_name = f"{self._interval_name} Remaining"

    @property
    def native_value(self) -> float | None:
        """Return miles/km remaining (mileage) or days remaining (time)."""
        if self._interval_type == INTERVAL_TYPE_TIME:
            return self._time_remaining()
        return self._mileage_remaining()

    def _mileage_remaining(self) -> float | None:
        """Compute miles or km remaining."""
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

    def _time_remaining(self) -> float | None:
        """Compute days remaining until service is due."""
        due = _compute_due_date({
            "last_serviced_date": self._last_serviced_date,
            "period": self._period,
            "interval_value": self._interval_value,
        })
        if due is None:
            return None
        return (due - date.today()).days

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit."""
        if self._interval_type == INTERVAL_TYPE_TIME:
            return UnitOfTime.DAYS
        if self._units == UNITS_METRIC:
            return UnitOfLength.KILOMETERS
        return UnitOfLength.MILES

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs: dict[str, Any] = {
            "service_name": self._interval_name,
            "type": self._interval_type,
        }

        if self._interval_type == INTERVAL_TYPE_TIME:
            attrs["interval_value"] = self._interval_value
            attrs["period"] = self._period
            attrs["recurring"] = self._recurring
            attrs["last_serviced_date"] = self._last_serviced_date
            due = _compute_due_date({
                "last_serviced_date": self._last_serviced_date,
                "period": self._period,
                "interval_value": self._interval_value,
            })
            if due:
                attrs["due_date"] = due.isoformat()
        else:
            attrs["interval_miles"] = self._interval_miles
            attrs["last_serviced_mileage"] = self._last_serviced_mileage

        value = self.native_value
        if value is not None:
            attrs["overdue"] = value < 0
        return attrs
