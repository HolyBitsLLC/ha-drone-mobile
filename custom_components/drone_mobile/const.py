"""Constants for the DroneMobile integration."""

DOMAIN = "drone_mobile"
MANUFACTURER = "DroneMobile (Firstech/Compustar)"

CONF_VEHICLE_ID = "vehicle_id"
CONF_UNITS = "units"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_SERVICE_INTERVALS = "service_intervals"

DEFAULT_UNITS = "imperial"
DEFAULT_UPDATE_INTERVAL = 5  # minutes

UNITS_IMPERIAL = "imperial"
UNITS_METRIC = "metric"
UNIT_OPTIONS = [UNITS_IMPERIAL, UNITS_METRIC]

# Commands
CMD_START = "start"
CMD_STOP = "stop"
CMD_LOCK = "lock"
CMD_UNLOCK = "unlock"
CMD_TRUNK = "trunk"
CMD_PANIC_ON = "panic_on"
CMD_PANIC_OFF = "panic_off"
CMD_AUX1 = "aux1"
CMD_AUX2 = "aux2"
CMD_LOCATION = "location"
