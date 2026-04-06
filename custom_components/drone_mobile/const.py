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

# Service interval types
INTERVAL_TYPE_MILEAGE = "mileage"
INTERVAL_TYPE_TIME = "time"
INTERVAL_TYPES = [INTERVAL_TYPE_MILEAGE, INTERVAL_TYPE_TIME]

# Time interval period choices (stored as days internally)
TIME_PERIOD_DAYS = "days"
TIME_PERIOD_WEEKS = "weeks"
TIME_PERIOD_MONTHS = "months"
TIME_PERIODS = [TIME_PERIOD_DAYS, TIME_PERIOD_WEEKS, TIME_PERIOD_MONTHS]

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
