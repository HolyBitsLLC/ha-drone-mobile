"""Config flow for DroneMobile integration."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

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
    INTERVAL_TYPE_MILEAGE,
    INTERVAL_TYPE_TIME,
    TIME_PERIOD_DAYS,
    TIME_PERIOD_MONTHS,
    TIME_PERIOD_WEEKS,
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


VALID_TYPES = {INTERVAL_TYPE_MILEAGE, INTERVAL_TYPE_TIME}
VALID_PERIODS = {TIME_PERIOD_DAYS, TIME_PERIOD_WEEKS, TIME_PERIOD_MONTHS}

# Required CSV columns
_CSV_COLUMNS = {
    "name", "type", "interval_miles", "last_serviced_mileage",
    "interval_value", "period", "recurring", "last_serviced_date",
}


def _parse_csv_intervals(
    csv_text: str,
) -> tuple[list[dict[str, Any]], str | None]:
    """Parse CSV text into a list of service interval dicts.

    Returns (intervals, error_message).  error_message is None on success.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return [], "No header row found"

    # Normalize header names
    fields = {f.strip().lower() for f in reader.fieldnames}
    if "name" not in fields or "type" not in fields:
        return [], "CSV must have at least 'name' and 'type' columns"

    intervals: list[dict[str, Any]] = []
    for row_num, row in enumerate(reader, start=2):
        # Normalize keys
        row = {k.strip().lower(): v.strip() if v else "" for k, v in row.items()}
        name = row.get("name", "").strip()
        if not name:
            return [], f"Row {row_num}: missing name"

        interval_type = row.get("type", "mileage").lower()
        if interval_type not in VALID_TYPES:
            return [], (
                f"Row {row_num} ({name}): "
                f"type must be 'mileage' or 'time', got '{interval_type}'"
            )

        if interval_type == INTERVAL_TYPE_MILEAGE:
            try:
                miles = int(row.get("interval_miles") or "5000")
            except ValueError:
                return [], (
                    f"Row {row_num} ({name}): "
                    f"interval_miles must be an integer"
                )
            try:
                last_mi = int(row.get("last_serviced_mileage") or "0")
            except ValueError:
                return [], (
                    f"Row {row_num} ({name}): "
                    f"last_serviced_mileage must be an integer"
                )
            intervals.append({
                "name": name,
                "type": INTERVAL_TYPE_MILEAGE,
                "interval_miles": miles,
                "last_serviced_mileage": last_mi,
            })
        else:
            try:
                value = int(row.get("interval_value") or "6")
            except ValueError:
                return [], (
                    f"Row {row_num} ({name}): "
                    f"interval_value must be an integer"
                )
            period = (row.get("period") or "months").lower()
            if period not in VALID_PERIODS:
                return [], (
                    f"Row {row_num} ({name}): "
                    f"period must be days/weeks/months, got '{period}'"
                )
            recurring_str = (row.get("recurring") or "true").lower()
            recurring = recurring_str in ("true", "1", "yes")
            last_date = row.get("last_serviced_date", "")
            intervals.append({
                "name": name,
                "type": INTERVAL_TYPE_TIME,
                "interval_value": value,
                "period": period,
                "recurring": recurring,
                "last_serviced_date": last_date,
            })

    if not intervals:
        return [], "No data rows found in CSV"

    return intervals, None


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
        return DroneMobileOptionsFlow()

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

    def __init__(self) -> None:
        """Initialize options flow."""
        self._service_intervals: list[dict[str, Any]] = []
        self._edit_index: int | None = None

    def _build_options(self, user_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the full options dict preserving service intervals."""
        base = dict(self.config_entry.options)
        if user_data:
            base.update(user_data)
        base[CONF_SERVICE_INTERVALS] = self._service_intervals
        return base

    def _interval_summary(self, s: dict[str, Any]) -> str:
        """Build a human-readable summary for one interval."""
        if s.get("type", INTERVAL_TYPE_MILEAGE) == INTERVAL_TYPE_TIME:
            period = s.get("period", TIME_PERIOD_DAYS)
            every = s.get("interval_value", 0)
            recurring = "recurring" if s.get("recurring", True) else "one-time"
            last = s.get("last_serviced_date", "never")
            return f"{s['name']} (every {every} {period}, {recurring}, last: {last})"
        miles = s.get("interval_miles", 0)
        last = s.get("last_serviced_mileage", 0)
        return f"{s['name']} (every {miles} mi, last at {last} mi)"

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the options menu."""
        if not self._service_intervals and self.config_entry.options.get(CONF_SERVICE_INTERVALS):
            self._service_intervals = list(
                self.config_entry.options[CONF_SERVICE_INTERVALS]
            )

        if user_input is not None:
            next_step = user_input.get("next_step")
            if next_step == "general":
                return await self.async_step_general()
            if next_step == "service_intervals":
                return await self.async_step_service_intervals()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("next_step", default="general"): vol.In(
                        {
                            "general": "General Settings",
                            "service_intervals": "Service Intervals",
                        }
                    ),
                }
            ),
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
        if user_input is not None:
            action = user_input.get("action")
            if action == "add":
                return await self.async_step_select_interval_type()
            if action == "edit":
                return await self.async_step_select_edit_interval()
            if action == "remove":
                return await self.async_step_remove_service_interval()
            if action == "import_csv":
                return await self.async_step_import_csv()
            if action == "done":
                return self.async_create_entry(
                    title="", data=self._build_options()
                )

        actions: dict[str, str] = {"add": "Add New Interval"}
        if self._service_intervals:
            actions["edit"] = "Edit Existing Interval"
            actions["remove"] = "Remove Interval"
        actions["import_csv"] = "Import from CSV"
        actions["done"] = "Save & Close"

        desc = (
            "\n".join(
                f"• {self._interval_summary(s)}" for s in self._service_intervals
            )
            if self._service_intervals
            else "No service intervals configured."
        )

        return self.async_show_form(
            step_id="service_intervals",
            description_placeholders={"intervals": desc},
            data_schema=vol.Schema(
                {vol.Required("action", default="add"): vol.In(actions)}
            ),
        )

    # ── Add flow ──────────────────────────────────────────────

    async def async_step_select_interval_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose between mileage-based or time-based interval."""
        if user_input is not None:
            interval_type = user_input["interval_type"]
            if interval_type == INTERVAL_TYPE_MILEAGE:
                return await self.async_step_add_mileage_interval()
            return await self.async_step_add_time_interval()

        return self.async_show_form(
            step_id="select_interval_type",
            data_schema=vol.Schema(
                {
                    vol.Required("interval_type", default=INTERVAL_TYPE_MILEAGE): vol.In(
                        {
                            INTERVAL_TYPE_MILEAGE: "Mileage-Based",
                            INTERVAL_TYPE_TIME: "Time-Based",
                        }
                    ),
                }
            ),
        )

    async def async_step_add_mileage_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a mileage-based service interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input["name"].strip()
            if self._name_exists(name):
                errors["name"] = "duplicate_name"
            else:
                self._service_intervals.append(
                    {
                        "name": name,
                        "type": INTERVAL_TYPE_MILEAGE,
                        "interval_miles": user_input["interval_miles"],
                        "last_serviced_mileage": user_input.get(
                            "last_serviced_mileage", 0
                        ),
                    }
                )
                return await self.async_step_service_intervals()

        return self.async_show_form(
            step_id="add_mileage_interval",
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

    async def async_step_add_time_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a time-based service interval."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input["name"].strip()
            if self._name_exists(name):
                errors["name"] = "duplicate_name"
            else:
                self._service_intervals.append(
                    {
                        "name": name,
                        "type": INTERVAL_TYPE_TIME,
                        "interval_value": user_input["interval_value"],
                        "period": user_input["period"],
                        "recurring": user_input.get("recurring", True),
                        "last_serviced_date": user_input.get(
                            "last_serviced_date", ""
                        ),
                    }
                )
                return await self.async_step_service_intervals()

        return self.async_show_form(
            step_id="add_time_interval",
            data_schema=vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required("interval_value", default=6): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=365)
                    ),
                    vol.Required("period", default=TIME_PERIOD_MONTHS): vol.In(
                        {
                            TIME_PERIOD_DAYS: "Days",
                            TIME_PERIOD_WEEKS: "Weeks",
                            TIME_PERIOD_MONTHS: "Months",
                        }
                    ),
                    vol.Required("recurring", default=True): bool,
                    vol.Optional("last_serviced_date", default=""): str,
                }
            ),
            errors=errors,
        )

    # ── Edit flow ─────────────────────────────────────────────

    async def async_step_select_edit_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select an interval to edit."""
        if user_input is not None:
            name = user_input["name"]
            for i, s in enumerate(self._service_intervals):
                if s["name"] == name:
                    self._edit_index = i
                    break
            interval = self._service_intervals[self._edit_index]
            if interval.get("type", INTERVAL_TYPE_MILEAGE) == INTERVAL_TYPE_TIME:
                return await self.async_step_edit_time_interval()
            return await self.async_step_edit_mileage_interval()

        interval_names = {s["name"]: s["name"] for s in self._service_intervals}
        return self.async_show_form(
            step_id="select_edit_interval",
            data_schema=vol.Schema(
                {vol.Required("name"): vol.In(interval_names)}
            ),
        )

    async def async_step_edit_mileage_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit a mileage-based service interval."""
        errors: dict[str, str] = {}
        interval = self._service_intervals[self._edit_index]

        if user_input is not None:
            new_name = user_input["name"].strip()
            if new_name.lower() != interval["name"].lower() and self._name_exists(new_name):
                errors["name"] = "duplicate_name"
            else:
                self._service_intervals[self._edit_index] = {
                    "name": new_name,
                    "type": INTERVAL_TYPE_MILEAGE,
                    "interval_miles": user_input["interval_miles"],
                    "last_serviced_mileage": user_input.get(
                        "last_serviced_mileage", 0
                    ),
                }
                self._edit_index = None
                return await self.async_step_service_intervals()

        return self.async_show_form(
            step_id="edit_mileage_interval",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=interval["name"]): str,
                    vol.Required(
                        "interval_miles",
                        default=interval.get("interval_miles", 5000),
                    ): vol.All(vol.Coerce(int), vol.Range(min=100, max=100000)),
                    vol.Optional(
                        "last_serviced_mileage",
                        default=interval.get("last_serviced_mileage", 0),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0)),
                }
            ),
            errors=errors,
        )

    async def async_step_edit_time_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit a time-based service interval."""
        errors: dict[str, str] = {}
        interval = self._service_intervals[self._edit_index]

        if user_input is not None:
            new_name = user_input["name"].strip()
            if new_name.lower() != interval["name"].lower() and self._name_exists(new_name):
                errors["name"] = "duplicate_name"
            else:
                self._service_intervals[self._edit_index] = {
                    "name": new_name,
                    "type": INTERVAL_TYPE_TIME,
                    "interval_value": user_input["interval_value"],
                    "period": user_input["period"],
                    "recurring": user_input.get("recurring", True),
                    "last_serviced_date": user_input.get(
                        "last_serviced_date", ""
                    ),
                }
                self._edit_index = None
                return await self.async_step_service_intervals()

        return self.async_show_form(
            step_id="edit_time_interval",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=interval["name"]): str,
                    vol.Required(
                        "interval_value",
                        default=interval.get("interval_value", 6),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
                    vol.Required(
                        "period",
                        default=interval.get("period", TIME_PERIOD_MONTHS),
                    ): vol.In(
                        {
                            TIME_PERIOD_DAYS: "Days",
                            TIME_PERIOD_WEEKS: "Weeks",
                            TIME_PERIOD_MONTHS: "Months",
                        }
                    ),
                    vol.Required(
                        "recurring",
                        default=interval.get("recurring", True),
                    ): bool,
                    vol.Optional(
                        "last_serviced_date",
                        default=interval.get("last_serviced_date", ""),
                    ): str,
                }
            ),
            errors=errors,
        )

    # ── Import CSV flow ─────────────────────────────────────────

    async def async_step_import_csv(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Import service intervals from CSV text."""
        errors: dict[str, str] = {}

        if user_input is not None:
            csv_text = user_input.get("csv_data", "").strip()
            if not csv_text:
                errors["csv_data"] = "empty_csv"
            else:
                parsed, error = _parse_csv_intervals(csv_text)
                if error:
                    errors["csv_data"] = "invalid_csv"
                    self._csv_error_detail = error
                else:
                    added = 0
                    skipped = 0
                    for interval in parsed:
                        if self._name_exists(interval["name"]):
                            skipped += 1
                        else:
                            self._service_intervals.append(interval)
                            added += 1
                    _LOGGER.info(
                        "CSV import: %d added, %d skipped (duplicate)",
                        added,
                        skipped,
                    )
                    return await self.async_step_service_intervals()

        sample = (
            "name,type,interval_miles,last_serviced_mileage,"
            "interval_value,period,recurring,last_serviced_date\n"
            "Oil Change,mileage,5000,43000,,,,\n"
            "Annual Inspection,time,,,12,months,true,2026-01-15"
        )

        return self.async_show_form(
            step_id="import_csv",
            description_placeholders={"csv_example": sample},
            data_schema=vol.Schema(
                {
                    vol.Required("csv_data"): TextSelector(
                        TextSelectorConfig(multiline=True)
                    )
                }
            ),
            errors=errors,
        )

    # ── Remove flow ───────────────────────────────────────────

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

    # ── Helpers ────────────────────────────────────────────────

    def _name_exists(self, name: str, exclude_index: int | None = None) -> bool:
        """Check if a service interval name already exists."""
        for i, s in enumerate(self._service_intervals):
            if i == exclude_index:
                continue
            if s["name"].lower() == name.lower():
                return True
        return False
