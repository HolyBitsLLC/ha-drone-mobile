"""Config flow for DroneMobile integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from drone_mobile import DroneMobileClient
from drone_mobile.exceptions import AuthenticationError

from .const import (
    CONF_SERVICE_INTERVALS,
    CONF_UNITS,
    CONF_UPDATE_INTERVAL,
    CONF_VEHICLE_ID,
    DEFAULT_UNITS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    UNIT_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _validate_credentials(
    hass: HomeAssistant, username: str, password: str
) -> list[dict[str, Any]]:
    """Validate credentials and return vehicles list."""
    client = DroneMobileClient(username, password)
    try:
        vehicles = await hass.async_add_executor_job(client.get_vehicles)
    finally:
        if hasattr(client, "close"):
            await hass.async_add_executor_job(client.close)
    return vehicles


class DroneMobileConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DroneMobile."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._username: str | None = None
        self._password: str | None = None
        self._vehicles: list[dict[str, Any]] = []

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DroneMobileOptionsFlow:
        """Get the options flow for this handler."""
        return DroneMobileOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial credentials step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]

            try:
                self._vehicles = await _validate_credentials(
                    self.hass, self._username, self._password
                )
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "unknown"
            else:
                if not self._vehicles:
                    errors["base"] = "no_vehicles"
                else:
                    return await self.async_step_select_vehicle()

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    async def async_step_select_vehicle(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick which vehicle to configure."""
        if user_input is not None:
            vehicle_id = user_input[CONF_VEHICLE_ID]
            vehicle_name = next(
                (
                    v.name
                    for v in self._vehicles
                    if str(v.vehicle_id) == str(vehicle_id)
                ),
                f"Vehicle {vehicle_id}",
            )

            await self.async_set_unique_id(f"drone_mobile_{vehicle_id}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=vehicle_name,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                    CONF_VEHICLE_ID: str(vehicle_id),
                },
                options={
                    CONF_UNITS: DEFAULT_UNITS,
                    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                    CONF_SERVICE_INTERVALS: [],
                },
            )

        # Build vehicle options, excluding already-configured vehicles
        existing_ids = {
            entry.data[CONF_VEHICLE_ID]
            for entry in self._async_current_entries()
        }
        vehicle_options = {
            str(v.vehicle_id): v.name
            for v in self._vehicles
            if str(v.vehicle_id) not in existing_ids
        }

        if not vehicle_options:
            return self.async_abort(reason="already_configured")

        return self.async_show_form(
            step_id="select_vehicle",
            data_schema=vol.Schema(
                {vol.Required(CONF_VEHICLE_ID): vol.In(vehicle_options)}
            ),
        )


class DroneMobileOptionsFlow(config_entries.OptionsFlow):
    """Handle DroneMobile options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self._service_intervals: list[dict[str, Any]] = list(
            config_entry.options.get(CONF_SERVICE_INTERVALS, [])
        )

    def _build_options(self, user_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the full options dict preserving service intervals."""
        base = dict(self.config_entry.options)
        if user_data:
            base.update(user_data)
        base[CONF_SERVICE_INTERVALS] = self._service_intervals
        return base

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["general", "service_intervals"],
        )

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage general options (units, update interval)."""
        if user_input is not None:
            return self.async_create_entry(
                title="", data=self._build_options(user_input)
            )

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UNITS,
                        default=self.config_entry.options.get(
                            CONF_UNITS, DEFAULT_UNITS
                        ),
                    ): vol.In(UNIT_OPTIONS),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=2, max=60)),
                }
            ),
        )

    async def async_step_service_intervals(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the service intervals management menu."""
        menu_options = ["add_service_interval"]
        if self._service_intervals:
            menu_options.append("remove_service_interval")
        menu_options.append("done_service_intervals")

        return self.async_show_menu(
            step_id="service_intervals",
            menu_options=menu_options,
        )

    async def async_step_add_service_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new service interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input["name"].strip()
            interval_miles = user_input["interval_miles"]

            # Check for duplicate names
            existing_names = {s["name"].lower() for s in self._service_intervals}
            if name.lower() in existing_names:
                errors["name"] = "duplicate_name"
            else:
                self._service_intervals.append(
                    {
                        "name": name,
                        "interval_miles": interval_miles,
                        "last_serviced_mileage": user_input.get(
                            "last_serviced_mileage", 0
                        ),
                    }
                )
                return await self.async_step_service_intervals()

        return self.async_show_form(
            step_id="add_service_interval",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required("interval_miles", default=5000): vol.All(
                        vol.Coerce(int), vol.Range(min=100, max=100000)
                    ),
                    vol.Optional("last_serviced_mileage", default=0): vol.All(
                        vol.Coerce(int), vol.Range(min=0)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_remove_service_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a service interval."""
        if user_input is not None:
            name_to_remove = user_input["name"]
            self._service_intervals = [
                s for s in self._service_intervals if s["name"] != name_to_remove
            ]
            return await self.async_step_service_intervals()

        interval_names = {s["name"]: s["name"] for s in self._service_intervals}

        return self.async_show_form(
            step_id="remove_service_interval",
            data_schema=vol.Schema(
                {vol.Required("name"): vol.In(interval_names)}
            ),
        )

    async def async_step_done_service_intervals(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Save and finish service interval editing."""
        return self.async_create_entry(
            title="", data=self._build_options()
        )
