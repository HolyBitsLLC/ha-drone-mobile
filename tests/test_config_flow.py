"""Tests for DroneMobile config flow."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_vehicle():
    """Return a mock vehicle for config flow."""
    vehicle = MagicMock()
    vehicle.vehicle_id = "12345"
    vehicle.name = "My Honda Civic"
    return vehicle


@pytest.mark.asyncio
async def test_validate_credentials_success(mock_vehicle):
    """Test successful credential validation."""
    from custom_components.drone_mobile.config_flow import _validate_credentials

    hass = MagicMock()
    hass.async_add_executor_job = lambda func, *args: _run_sync(func, *args)

    with patch(
        "custom_components.drone_mobile.config_flow.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicles.return_value = [mock_vehicle]
        client.close = MagicMock()
        mock_cls.return_value = client

        vehicles = await _validate_credentials(hass, "test@example.com", "password")
        assert len(vehicles) == 1
        assert vehicles[0].name == "My Honda Civic"


@pytest.mark.asyncio
async def test_validate_credentials_auth_error():
    """Test authentication error handling."""
    from drone_mobile.exceptions import AuthenticationError

    from custom_components.drone_mobile.config_flow import _validate_credentials

    hass = MagicMock()
    hass.async_add_executor_job = lambda func, *args: _run_sync(func, *args)

    with patch(
        "custom_components.drone_mobile.config_flow.DroneMobileClient"
    ) as mock_cls:
        client = MagicMock()
        client.get_vehicles.side_effect = AuthenticationError("bad creds")
        client.close = MagicMock()
        mock_cls.return_value = client

        with pytest.raises(AuthenticationError):
            await _validate_credentials(hass, "bad@example.com", "wrong")


async def _run_sync(func, *args):
    """Helper to run sync functions in tests."""
    return func(*args)
