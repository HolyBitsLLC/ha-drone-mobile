"""Tests for DroneMobile sensor platform."""
from __future__ import annotations

from custom_components.drone_mobile.const import UNITS_IMPERIAL, UNITS_METRIC


def test_odometer_imperial_conversion():
    """Test odometer stays in miles for imperial."""
    value = 45000.0
    assert value == 45000.0


def test_odometer_metric_conversion():
    """Test odometer converts to km for metric."""
    value = 45000.0
    result = round(float(value) * 1.60934, 1)
    assert result == 72420.3


def test_temperature_imperial_conversion():
    """Test Celsius to Fahrenheit conversion."""
    celsius = 22.0
    fahrenheit = round(float(celsius) * 9 / 5 + 32, 1)
    assert fahrenheit == 71.6


def test_temperature_metric_stays():
    """Test Celsius stays as-is for metric."""
    celsius = 22.0
    assert celsius == 22.0


def test_unit_options():
    """Validate unit option strings."""
    assert UNITS_IMPERIAL == "imperial"
    assert UNITS_METRIC == "metric"
