"""Test fixtures for DroneMobile integration tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_vehicle_status():
    """Return a mock VehicleStatus."""
    status = MagicMock()
    status.is_running = False
    status.is_locked = True
    status.battery_voltage = 12.6
    status.battery_percent = 85
    status.odometer = 45000.0
    status.fuel_level = 72
    status.interior_temperature = 22.0
    status.exterior_temperature = 18.0
    status.last_updated = None
    location = MagicMock()
    location.latitude = 40.7128
    location.longitude = -74.0060
    status.location = location
    return status


@pytest.fixture
def mock_vehicle_info():
    """Return a mock VehicleInfo."""
    info = MagicMock()
    info.make = "Honda"
    info.model = "Civic"
    info.year = 2023
    info.color = "Blue"
    info.vin = "1HGCV1F3XPA000001"
    return info


@pytest.fixture
def mock_vehicle(mock_vehicle_status, mock_vehicle_info):
    """Return a mock Vehicle."""
    vehicle = MagicMock()
    vehicle.vehicle_id = "12345"
    vehicle.device_key = "dk_abc123"
    vehicle.name = "My Honda Civic"
    vehicle.info = mock_vehicle_info
    vehicle.get_status.return_value = mock_vehicle_status
    vehicle.start.return_value = MagicMock(success=True)
    vehicle.stop.return_value = MagicMock(success=True)
    vehicle.lock.return_value = MagicMock(success=True)
    vehicle.unlock.return_value = MagicMock(success=True)
    vehicle.trunk.return_value = MagicMock(success=True)
    vehicle.panic_on.return_value = MagicMock(success=True)
    vehicle.panic_off.return_value = MagicMock(success=True)
    vehicle.aux1.return_value = MagicMock(success=True)
    vehicle.aux2.return_value = MagicMock(success=True)
    vehicle.get_location.return_value = MagicMock(success=True)
    return vehicle


@pytest.fixture
def mock_client(mock_vehicle):
    """Return a mock DroneMobileClient."""
    with patch("custom_components.drone_mobile.coordinator.DroneMobileClient") as mock_cls:
        client = MagicMock()
        client.get_vehicles.return_value = [mock_vehicle]
        client.get_vehicle.return_value = mock_vehicle
        mock_cls.return_value = client
        yield client


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    from unittest.mock import MagicMock

    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "username": "test@example.com",
        "password": "test_password",
        "vehicle_id": "12345",
    }
    entry.options = {
        "units": "imperial",
        "update_interval": 5,
    }
    return entry
