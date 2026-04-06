"""Sensor platform for DroneMobile."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_UNITS, DEFAULT_UNITS, DOMAIN, UNITS_METRIC
from .coordinator import DroneMobileCoordinator
from .entity import DroneMobileEntity

SENSOR_DESCRIPTIONS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:car-battery",
    ),
    SensorEntityDescription(
        key="battery_percent",
        translation_key="battery_percent",
        name="Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="odometer",
        translation_key="odometer",
        name="Odometer",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DISTANCE,
    ),
    SensorEntityDescription(
        key="fuel_level",
        translation_key="fuel_level",
        name="Fuel Level",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:gas-station",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="interior_temperature",
        translation_key="interior_temperature",
        name="Interior Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="exterior_temperature",
        translation_key="exterior_temperature",
        name="Exterior Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="last_updated",
        translation_key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up DroneMobile sensors."""
    coordinator: DroneMobileCoordinator = hass.data[DOMAIN][entry.entry_id]
    units = entry.options.get(CONF_UNITS, DEFAULT_UNITS)
    async_add_entities(
        DroneMobileSensor(coordinator, desc, units) for desc in SENSOR_DESCRIPTIONS
    )


class DroneMobileSensor(DroneMobileEntity, SensorEntity):
    """Representation of a DroneMobile sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: DroneMobileCoordinator,
        description: SensorEntityDescription,
        units: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._units = units

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value."""
        status = self.coordinator.data.get("status", {})
        value = status.get(self.entity_description.key)
        if value is None:
            return None

        key = self.entity_description.key

        # Unit conversions
        if key == "odometer" and value is not None:
            if self._units == UNITS_METRIC:
                return round(float(value) * 1.60934, 1)
            return value

        if key in ("interior_temperature", "exterior_temperature") and value is not None:
            if self._units != UNITS_METRIC:
                # API returns Celsius; convert to Fahrenheit for imperial
                return round(float(value) * 9 / 5 + 32, 1)
            return value

        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        key = self.entity_description.key
        if key == "odometer":
            if self._units == UNITS_METRIC:
                return UnitOfLength.KILOMETERS
            return UnitOfLength.MILES
        if key in ("interior_temperature", "exterior_temperature"):
            if self._units == UNITS_METRIC:
                return UnitOfTemperature.CELSIUS
            return UnitOfTemperature.FAHRENHEIT
        return self.entity_description.native_unit_of_measurement
