"""Tests for DroneMobile constants."""
from custom_components.drone_mobile.const import (
    CMD_AUX1,
    CMD_AUX2,
    CMD_LOCK,
    CMD_PANIC_OFF,
    CMD_PANIC_ON,
    CMD_START,
    CMD_STOP,
    CMD_TRUNK,
    CMD_UNLOCK,
    DEFAULT_UNITS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MANUFACTURER,
    UNIT_OPTIONS,
    UNITS_IMPERIAL,
    UNITS_METRIC,
)


def test_domain():
    assert DOMAIN == "drone_mobile"


def test_manufacturer():
    assert "DroneMobile" in MANUFACTURER


def test_defaults():
    assert DEFAULT_UNITS == "imperial"
    assert DEFAULT_UPDATE_INTERVAL == 5


def test_unit_options():
    assert UNITS_IMPERIAL in UNIT_OPTIONS
    assert UNITS_METRIC in UNIT_OPTIONS


def test_commands():
    assert CMD_START == "start"
    assert CMD_STOP == "stop"
    assert CMD_LOCK == "lock"
    assert CMD_UNLOCK == "unlock"
    assert CMD_TRUNK == "trunk"
    assert CMD_PANIC_ON == "panic_on"
    assert CMD_PANIC_OFF == "panic_off"
    assert CMD_AUX1 == "aux1"
    assert CMD_AUX2 == "aux2"
