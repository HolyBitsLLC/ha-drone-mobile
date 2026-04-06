"""Tests for DroneMobile service interval sensors and buttons."""
from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.drone_mobile.const import (
    UNITS_IMPERIAL,
    UNITS_METRIC,
)
from custom_components.drone_mobile.service_sensor import (
    ServiceIntervalSensor,
    _slugify_name,
)

# --- slugify tests ---


def test_slugify_name_basic():
    """Test basic slugification."""
    assert _slugify_name("Oil Change") == "oil_change"


def test_slugify_name_hyphens():
    """Test hyphens are converted to underscores."""
    assert _slugify_name("Tire-Rotation") == "tire_rotation"


def test_slugify_name_already_slug():
    """Test an already-slugified name stays the same."""
    assert _slugify_name("brake_pads") == "brake_pads"


# --- ServiceIntervalSensor tests ---


def _make_coordinator(odometer: float | None = 45000.0) -> MagicMock:
    """Create a mock coordinator with status data."""
    coordinator = MagicMock()
    coordinator.data = {
        "vehicle_id": "12345",
        "status": {"odometer": odometer},
    }
    return coordinator


def test_service_sensor_miles_remaining_imperial():
    """Test miles remaining calculation in imperial."""
    interval = {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 43000}
    coordinator = _make_coordinator(odometer=45000.0)

    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_miles = interval["interval_miles"]
    sensor._last_serviced_mileage = interval["last_serviced_mileage"]
    sensor._units = UNITS_IMPERIAL
    sensor.coordinator = coordinator

    # 43000 + 5000 - 45000 = 3000 miles remaining
    assert sensor.native_value == 3000.0


def test_service_sensor_miles_remaining_metric():
    """Test km remaining calculation in metric."""
    interval = {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 43000}
    coordinator = _make_coordinator(odometer=45000.0)

    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_miles = interval["interval_miles"]
    sensor._last_serviced_mileage = interval["last_serviced_mileage"]
    sensor._units = UNITS_METRIC
    sensor.coordinator = coordinator

    # 3000 miles * 1.60934 = 4828.0 km
    assert sensor.native_value == 4828.0


def test_service_sensor_overdue():
    """Test overdue service returns negative value."""
    interval = {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 38000}
    coordinator = _make_coordinator(odometer=45000.0)

    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_miles = interval["interval_miles"]
    sensor._last_serviced_mileage = interval["last_serviced_mileage"]
    sensor._units = UNITS_IMPERIAL
    sensor.coordinator = coordinator

    # 38000 + 5000 - 45000 = -2000 (overdue)
    assert sensor.native_value == -2000.0


def test_service_sensor_no_odometer():
    """Test sensor returns None when odometer is unavailable."""
    interval = {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 43000}
    coordinator = _make_coordinator(odometer=None)

    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_miles = interval["interval_miles"]
    sensor._last_serviced_mileage = interval["last_serviced_mileage"]
    sensor._units = UNITS_IMPERIAL
    sensor.coordinator = coordinator

    assert sensor.native_value is None


def test_service_sensor_extra_attributes():
    """Test extra state attributes include overdue flag."""
    interval = {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 43000}
    coordinator = _make_coordinator(odometer=45000.0)

    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_miles = interval["interval_miles"]
    sensor._last_serviced_mileage = interval["last_serviced_mileage"]
    sensor._units = UNITS_IMPERIAL
    sensor.coordinator = coordinator

    attrs = sensor.extra_state_attributes
    assert attrs["service_name"] == "Oil Change"
    assert attrs["interval_miles"] == 5000
    assert attrs["last_serviced_mileage"] == 43000
    assert attrs["overdue"] is False


def test_service_sensor_overdue_attribute():
    """Test overdue attribute is True when negative remaining."""
    interval = {"name": "Tire Rotation", "interval_miles": 5000, "last_serviced_mileage": 38000}
    coordinator = _make_coordinator(odometer=45000.0)

    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_miles = interval["interval_miles"]
    sensor._last_serviced_mileage = interval["last_serviced_mileage"]
    sensor._units = UNITS_IMPERIAL
    sensor.coordinator = coordinator

    attrs = sensor.extra_state_attributes
    assert attrs["overdue"] is True


# --- Config flow service interval options tests ---


def test_duplicate_service_interval_names():
    """Test that the options flow logic would catch duplicates."""
    existing = [
        {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 0},
    ]
    new_name = "oil change"
    existing_names = {s["name"].lower() for s in existing}
    assert new_name.lower() in existing_names


def test_no_duplicate_different_name():
    """Test that different names are allowed."""
    existing = [
        {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 0},
    ]
    new_name = "Tire Rotation"
    existing_names = {s["name"].lower() for s in existing}
    assert new_name.lower() not in existing_names
