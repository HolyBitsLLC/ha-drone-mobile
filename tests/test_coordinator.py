"""Tests for DroneMobile coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.drone_mobile.coordinator import DroneMobileCoordinator


@pytest.fixture
def mock_entry():
    """Return a mock config entry."""
    entry = MagicMock()
    entry.data = {
        "username": "test@example.com",
        "password": "test_password",
        "vehicle_id": "12345",
    }
    entry.options = {"update_interval": 5}
    return entry


@pytest.fixture
def mock_vehicle_status():
    """Return a mock VehicleStatus object."""
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
    """Return a mock VehicleInfo object."""
    info = MagicMock()
    info.make = "Honda"
    info.model = "Civic"
    info.year = 2023
    info.color = "Blue"
    info.vin = "1HGCV1F3XPA000001"
    return info


@pytest.fixture
def mock_vehicle(mock_vehicle_status, mock_vehicle_info):
    """Return a mock Vehicle object."""
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
    return vehicle


async def test_coordinator_update(hass: HomeAssistant, mock_entry, mock_vehicle):
    """Test coordinator fetches and normalizes data."""
    with patch(
        "custom_components.drone_mobile.coordinator.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicle.return_value = mock_vehicle
        mock_cls.return_value = client

        coordinator = DroneMobileCoordinator(hass, mock_entry)
        data = await coordinator._async_update_data()

        assert data["vehicle_id"] == "12345"
        assert data["device_key"] == "dk_abc123"
        assert data["name"] == "My Honda Civic"
        assert data["status"]["is_running"] is False
        assert data["status"]["is_locked"] is True
        assert data["status"]["battery_voltage"] == 12.6
        assert data["status"]["odometer"] == 45000.0
        assert data["location"]["latitude"] == 40.7128
        assert data["location"]["longitude"] == -74.0060
        assert data["info"]["make"] == "Honda"
        assert data["info"]["year"] == 2023


async def test_coordinator_update_no_location(
    hass: HomeAssistant, mock_entry, mock_vehicle
):
    """Test coordinator handles missing GPS correctly."""
    mock_vehicle.get_status.return_value.location = None

    with patch(
        "custom_components.drone_mobile.coordinator.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicle.return_value = mock_vehicle
        mock_cls.return_value = client

        coordinator = DroneMobileCoordinator(hass, mock_entry)
        data = await coordinator._async_update_data()

        assert data["location"] is None


async def test_coordinator_send_command(
    hass: HomeAssistant, mock_entry, mock_vehicle
):
    """Test coordinator sends commands to the vehicle."""
    with patch(
        "custom_components.drone_mobile.coordinator.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicle.return_value = mock_vehicle
        mock_cls.return_value = client

        coordinator = DroneMobileCoordinator(hass, mock_entry)
        # Prevent actual refresh
        coordinator.async_request_refresh = AsyncMock()

        result = await coordinator.async_send_command("start")

        mock_vehicle.start.assert_called_once()
        assert result["success"] is True


async def test_coordinator_send_unknown_command(
    hass: HomeAssistant, mock_entry, mock_vehicle
):
    """Test coordinator rejects unknown commands."""
    with patch(
        "custom_components.drone_mobile.coordinator.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicle.return_value = mock_vehicle
        mock_cls.return_value = client

        coordinator = DroneMobileCoordinator(hass, mock_entry)

        with pytest.raises(ValueError, match="Unknown command"):
            await coordinator.async_send_command("invalid_cmd")


async def test_coordinator_auth_error(hass: HomeAssistant, mock_entry):
    """Test coordinator raises UpdateFailed on auth error."""
    from drone_mobile.exceptions import AuthenticationError
    from homeassistant.helpers.update_coordinator import UpdateFailed

    with patch(
        "custom_components.drone_mobile.coordinator.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicle.side_effect = AuthenticationError("bad creds")
        mock_cls.return_value = client

        coordinator = DroneMobileCoordinator(hass, mock_entry)

        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator._async_update_data()
