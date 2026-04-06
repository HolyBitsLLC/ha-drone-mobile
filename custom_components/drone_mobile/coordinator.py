"""DataUpdateCoordinator for DroneMobile."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from drone_mobile import DroneMobileClient
from drone_mobile.exceptions import AuthenticationError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import CONF_UPDATE_INTERVAL, CONF_VEHICLE_ID, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class DroneMobileCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage fetching DroneMobile data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self._username = entry.data[CONF_USERNAME]
        self._password = entry.data[CONF_PASSWORD]
        self._vehicle_id = entry.data[CONF_VEHICLE_ID]
        self._client: DroneMobileClient | None = None

        update_minutes = entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"DroneMobile {self._vehicle_id}",
            update_interval=timedelta(minutes=update_minutes),
        )

    def _get_client(self) -> DroneMobileClient:
        """Get or create the API client."""
        if self._client is None:
            self._client = DroneMobileClient(self._username, self._password)
        return self._client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the DroneMobile API."""
        try:
            client = self._get_client()
            vehicle = await self.hass.async_add_executor_job(
                client.get_vehicle, self._vehicle_id
            )
            status = await self.hass.async_add_executor_job(vehicle.get_status)

            # Build a normalized data dict for entities to consume
            data: dict[str, Any] = {
                "vehicle_id": str(vehicle.vehicle_id),
                "device_key": str(vehicle.device_key),
                "name": vehicle.name,
                "info": {
                    "make": getattr(vehicle.info, "make", None) if vehicle.info else None,
                    "model": getattr(vehicle.info, "model", None) if vehicle.info else None,
                    "year": getattr(vehicle.info, "year", None) if vehicle.info else None,
                    "color": getattr(vehicle.info, "color", None) if vehicle.info else None,
                    "vin": getattr(vehicle.info, "vin", None) if vehicle.info else None,
                },
                "status": {
                    "is_running": status.is_running,
                    "is_locked": status.is_locked,
                    "battery_voltage": status.battery_voltage,
                    "battery_percent": status.battery_percent,
                    "odometer": status.odometer,
                    "fuel_level": status.fuel_level,
                    "interior_temperature": status.interior_temperature,
                    "exterior_temperature": status.exterior_temperature,
                    "last_updated": (
                        status.last_updated.isoformat()
                        if status.last_updated
                        else None
                    ),
                },
                "location": None,
            }

            if status.location:
                data["location"] = {
                    "latitude": status.location.latitude,
                    "longitude": status.location.longitude,
                }

            return data

        except AuthenticationError as err:
            raise UpdateFailed("Authentication failed — check credentials") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with DroneMobile: {err}") from err

    async def async_send_command(self, command: str) -> dict[str, Any]:
        """Send a command to the vehicle and refresh data."""
        client = self._get_client()
        vehicle = await self.hass.async_add_executor_job(
            client.get_vehicle, self._vehicle_id
        )

        cmd_map = {
            "start": vehicle.start,
            "stop": vehicle.stop,
            "lock": vehicle.lock,
            "unlock": vehicle.unlock,
            "trunk": vehicle.trunk,
            "panic_on": vehicle.panic_on,
            "panic_off": vehicle.panic_off,
            "aux1": vehicle.aux1,
            "aux2": vehicle.aux2,
            "location": vehicle.get_location,
        }

        cmd_func = cmd_map.get(command)
        if cmd_func is None:
            raise ValueError(f"Unknown command: {command}")

        response = await self.hass.async_add_executor_job(cmd_func)
        # Refresh data after command
        await self.async_request_refresh()
        return {"success": response.success if hasattr(response, "success") else True}
