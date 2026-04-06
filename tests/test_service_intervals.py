"""Tests for DroneMobile service interval sensors and buttons."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

from custom_components.drone_mobile import _migrate_service_intervals
from custom_components.drone_mobile.binary_sensor import ServiceIntervalOverdueBinarySensor
from custom_components.drone_mobile.config_flow import _parse_csv_intervals
from custom_components.drone_mobile.const import (
    INTERVAL_TYPE_MILEAGE,
    INTERVAL_TYPE_TIME,
    TIME_PERIOD_DAYS,
    TIME_PERIOD_MONTHS,
    TIME_PERIOD_WEEKS,
    UNITS_IMPERIAL,
    UNITS_METRIC,
)
from custom_components.drone_mobile.service_sensor import (
    ServiceIntervalSensor,
    _add_months,
    _compute_due_date,
    _slugify_name,
)

# --- slugify tests ---


def test_slugify_name_basic():
    """Test basic slugification."""
    assert _slugify_name("Oil Change") == "oil_change"


def test_slugify_name_hyphens():
    """Test hyphens are converted to underscores."""
    assert _slugify_name("Tire-Rotation") == "tire_rotation"


def test_slugify_name_already_slug():
    """Test an already-slugified name stays the same."""
    assert _slugify_name("brake_pads") == "brake_pads"


# --- Helper function tests ---


def test_add_months_basic():
    """Test adding months to a date."""
    assert _add_months(date(2026, 1, 15), 6) == date(2026, 7, 15)


def test_add_months_year_wrap():
    """Test adding months across year boundary."""
    assert _add_months(date(2026, 11, 1), 3) == date(2027, 2, 1)


def test_add_months_clamp_day():
    """Test day clamping when month has fewer days."""
    assert _add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_compute_due_date_months():
    """Test due date calculation with months."""
    interval = {
        "last_serviced_date": "2026-01-15",
        "period": TIME_PERIOD_MONTHS,
        "interval_value": 6,
    }
    assert _compute_due_date(interval) == date(2026, 7, 15)


def test_compute_due_date_weeks():
    """Test due date calculation with weeks."""
    interval = {
        "last_serviced_date": "2026-01-01",
        "period": TIME_PERIOD_WEEKS,
        "interval_value": 2,
    }
    assert _compute_due_date(interval) == date(2026, 1, 15)


def test_compute_due_date_days():
    """Test due date calculation with days."""
    interval = {
        "last_serviced_date": "2026-03-01",
        "period": TIME_PERIOD_DAYS,
        "interval_value": 30,
    }
    assert _compute_due_date(interval) == date(2026, 3, 31)


def test_compute_due_date_empty_date():
    """Test due date returns None with empty date."""
    interval = {
        "last_serviced_date": "",
        "period": TIME_PERIOD_MONTHS,
        "interval_value": 6,
    }
    assert _compute_due_date(interval) is None


def test_compute_due_date_bad_date():
    """Test due date returns None with invalid date string."""
    interval = {
        "last_serviced_date": "not-a-date",
        "period": TIME_PERIOD_MONTHS,
        "interval_value": 6,
    }
    assert _compute_due_date(interval) is None


# --- Mileage ServiceIntervalSensor tests ---


def _make_coordinator(odometer: float | None = 45000.0) -> MagicMock:
    """Create a mock coordinator with status data."""
    coordinator = MagicMock()
    coordinator.data = {
        "vehicle_id": "12345",
        "status": {"odometer": odometer},
    }
    return coordinator


def _make_mileage_sensor(
    interval: dict, units: str = UNITS_IMPERIAL, odometer: float | None = 45000.0
) -> ServiceIntervalSensor:
    """Create a mileage sensor without calling __init__ (avoids coordinator super())."""
    sensor = ServiceIntervalSensor.__new__(ServiceIntervalSensor)
    sensor._interval_name = interval["name"]
    sensor._interval_type = interval.get("type", INTERVAL_TYPE_MILEAGE)
    sensor._units = units
    sensor.coordinator = _make_coordinator(odometer)

    # Provide a mock config entry with this interval in options
    mock_entry = MagicMock()
    mock_entry.options = {"service_intervals": [interval]}
    sensor._entry = mock_entry
    return sensor


def test_service_sensor_miles_remaining_imperial():
    """Test miles remaining calculation in imperial."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 43000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor.native_value == 3000.0


def test_service_sensor_miles_remaining_metric():
    """Test km remaining calculation in metric."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 43000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_METRIC, 45000.0)
    assert sensor.native_value == 4828.0


def test_service_sensor_overdue():
    """Test overdue service returns negative value."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 38000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor.native_value == -2000.0


def test_service_sensor_remaining_capped_to_interval_imperial():
    """Remaining miles must not exceed configured interval."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 47000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor.native_value == 5000.0


def test_service_sensor_remaining_capped_to_interval_metric():
    """Remaining km must not exceed interval converted to km."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 47000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_METRIC, 45000.0)
    assert sensor.native_value == 8046.7


def test_service_sensor_no_odometer():
    """Test sensor returns None when odometer is unavailable."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 43000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, None)
    assert sensor.native_value is None


def test_service_sensor_extra_attributes():
    """Test extra state attributes for mileage interval."""
    interval = {
        "name": "Oil Change", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 43000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    attrs = sensor.extra_state_attributes
    assert attrs["service_name"] == "Oil Change"
    assert attrs["type"] == INTERVAL_TYPE_MILEAGE
    assert attrs["interval_miles"] == 5000
    assert attrs["last_serviced_mileage"] == 43000
    assert attrs["overdue"] is False


def test_service_sensor_overdue_attribute():
    """Test overdue attribute is True when negative remaining."""
    interval = {
        "name": "Tire Rotation", "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000, "last_serviced_mileage": 38000,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    attrs = sensor.extra_state_attributes
    assert attrs["overdue"] is True


def _make_overdue_binary_sensor(
    interval: dict, odometer: float | None = 45000.0
) -> ServiceIntervalOverdueBinarySensor:
    """Create overdue binary sensor without calling __init__."""
    sensor = ServiceIntervalOverdueBinarySensor.__new__(ServiceIntervalOverdueBinarySensor)
    sensor._interval_name = interval["name"]
    sensor._interval_type = interval.get("type", INTERVAL_TYPE_MILEAGE)
    sensor.coordinator = _make_coordinator(odometer)

    mock_entry = MagicMock()
    mock_entry.options = {"service_intervals": [interval]}
    sensor._entry = mock_entry
    return sensor


def test_overdue_binary_sensor_mileage_not_overdue():
    """Mileage overdue binary sensor stays off when interval is not overdue."""
    interval = {
        "name": "Oil Change",
        "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000,
        "last_serviced_mileage": 43000,
    }
    sensor = _make_overdue_binary_sensor(interval, 45000.0)
    assert sensor.is_on is False


def test_overdue_binary_sensor_mileage_overdue():
    """Mileage overdue binary sensor turns on when overdue."""
    interval = {
        "name": "Oil Change",
        "type": INTERVAL_TYPE_MILEAGE,
        "interval_miles": 5000,
        "last_serviced_mileage": 38000,
    }
    sensor = _make_overdue_binary_sensor(interval, 45000.0)
    assert sensor.is_on is True


def test_overdue_binary_sensor_time_not_overdue():
    """Time-based overdue binary sensor stays off before due date."""
    interval = {
        "name": "Cabin Filter",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 30,
        "period": TIME_PERIOD_DAYS,
        "last_serviced_date": (date.today() - timedelta(days=10)).isoformat(),
    }
    sensor = _make_overdue_binary_sensor(interval)
    assert sensor.is_on is False


def test_overdue_binary_sensor_time_overdue():
    """Time-based overdue binary sensor turns on when due date passed."""
    interval = {
        "name": "Cabin Filter",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 30,
        "period": TIME_PERIOD_DAYS,
        "last_serviced_date": (date.today() - timedelta(days=40)).isoformat(),
    }
    sensor = _make_overdue_binary_sensor(interval)
    assert sensor.is_on is True


# --- Time-based ServiceIntervalSensor tests ---


def test_time_sensor_days_remaining():
    """Test days remaining for a time-based interval."""
    # Work backwards: if last serviced 20 days ago with 30-day interval, 10 days remain
    last_date = (date.today() - timedelta(days=20)).isoformat()
    interval = {
        "name": "Cabin Filter",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 30,
        "period": TIME_PERIOD_DAYS,
        "recurring": True,
        "last_serviced_date": last_date,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor.native_value == 10


def test_time_sensor_overdue():
    """Test time-based interval overdue returns negative days."""
    last_date = (date.today() - timedelta(days=40)).isoformat()
    interval = {
        "name": "Cabin Filter",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 30,
        "period": TIME_PERIOD_DAYS,
        "recurring": True,
        "last_serviced_date": last_date,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor.native_value == -10


def test_time_sensor_no_date():
    """Test time sensor returns None when no last_serviced_date."""
    interval = {
        "name": "Annual Inspection",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 12,
        "period": TIME_PERIOD_MONTHS,
        "recurring": True,
        "last_serviced_date": "",
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor.native_value is None


def test_time_sensor_extra_attributes():
    """Test extra attributes for time-based interval."""
    last_date = "2026-01-15"
    interval = {
        "name": "Annual Inspection",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 12,
        "period": TIME_PERIOD_MONTHS,
        "recurring": True,
        "last_serviced_date": last_date,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    attrs = sensor.extra_state_attributes
    assert attrs["service_name"] == "Annual Inspection"
    assert attrs["type"] == INTERVAL_TYPE_TIME
    assert attrs["interval_value"] == 12
    assert attrs["period"] == TIME_PERIOD_MONTHS
    assert attrs["recurring"] is True
    assert attrs["last_serviced_date"] == "2026-01-15"
    assert attrs["due_date"] == "2027-01-15"


def test_time_sensor_weeks():
    """Test time sensor with weeks period."""
    last_date = (date.today() - timedelta(weeks=1)).isoformat()
    interval = {
        "name": "Check Tire Pressure",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 2,
        "period": TIME_PERIOD_WEEKS,
        "recurring": True,
        "last_serviced_date": last_date,
    }
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    # 2 weeks from 1 week ago = 1 week from now = 7 days
    assert sensor.native_value == 7


def test_time_sensor_unit_is_days():
    """Test time sensor unit of measurement is days."""
    interval = {
        "name": "Test",
        "type": INTERVAL_TYPE_TIME,
        "interval_value": 30,
        "period": TIME_PERIOD_DAYS,
        "last_serviced_date": "2026-01-01",
    }
    sensor = _make_mileage_sensor(interval)
    from homeassistant.const import UnitOfTime
    assert sensor.native_unit_of_measurement == UnitOfTime.DAYS


# --- Legacy interval backward compat ---


def test_legacy_interval_defaults_to_mileage():
    """Test that an interval without a 'type' field defaults to mileage."""
    interval = {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 43000}
    sensor = _make_mileage_sensor(interval, UNITS_IMPERIAL, 45000.0)
    assert sensor._interval_type == INTERVAL_TYPE_MILEAGE
    assert sensor.native_value == 3000.0


# --- Config flow service interval options tests ---


def test_duplicate_service_interval_names():
    """Test that the options flow logic would catch duplicates."""
    existing = [
        {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 0},
    ]
    new_name = "oil change"
    existing_names = {s["name"].lower() for s in existing}
    assert new_name.lower() in existing_names


def test_no_duplicate_different_name():
    """Test that different names are allowed."""
    existing = [
        {"name": "Oil Change", "interval_miles": 5000, "last_serviced_mileage": 0},
    ]
    new_name = "Tire Rotation"
    existing_names = {s["name"].lower() for s in existing}
    assert new_name.lower() not in existing_names


# --- CSV parsing tests ---


def test_csv_parse_mileage():
    """Test parsing mileage-based CSV rows."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "Oil Change,mileage,5000,43000,,,,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is None
    assert len(intervals) == 1
    assert intervals[0]["name"] == "Oil Change"
    assert intervals[0]["type"] == INTERVAL_TYPE_MILEAGE
    assert intervals[0]["interval_miles"] == 5000
    assert intervals[0]["last_serviced_mileage"] == 43000


def test_csv_parse_time():
    """Test parsing time-based CSV rows."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "Inspection,time,,,12,months,true,2026-01-15"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is None
    assert len(intervals) == 1
    assert intervals[0]["type"] == INTERVAL_TYPE_TIME
    assert intervals[0]["interval_value"] == 12
    assert intervals[0]["period"] == "months"
    assert intervals[0]["recurring"] is True
    assert intervals[0]["last_serviced_date"] == "2026-01-15"


def test_csv_parse_mixed():
    """Test parsing CSV with both types."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "Oil Change,mileage,5000,43000,,,,\n"
        "Inspection,time,,,12,months,true,2026-01-15"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is None
    assert len(intervals) == 2
    assert intervals[0]["type"] == INTERVAL_TYPE_MILEAGE
    assert intervals[1]["type"] == INTERVAL_TYPE_TIME


def test_csv_parse_no_header():
    """Test CSV with no header returns error."""
    csv_text = ""
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is not None
    assert "No data rows" in err or "No header" in err


def test_csv_parse_headerless_data():
    """Test CSV without header row auto-detects and parses correctly."""
    csv_text = (
        "Engine Oil,mileage,25000,50163,,,,\n"
        "Fuel Filter,mileage,15000,50163,,,,\n"
        "Front-End Grease,mileage,5000,50163,,,,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is None
    assert len(intervals) == 3
    assert intervals[0]["name"] == "Engine Oil"
    assert intervals[0]["interval_miles"] == 25000
    assert intervals[0]["last_serviced_mileage"] == 50163
    assert intervals[1]["name"] == "Fuel Filter"
    assert intervals[2]["name"] == "Front-End Grease"
    assert intervals[2]["interval_miles"] == 5000


def test_csv_parse_missing_name():
    """Test CSV with missing name returns error."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        ",mileage,5000,0,,,,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is not None
    assert "missing name" in err


def test_csv_parse_bad_type():
    """Test CSV with invalid type returns error."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "Oil Change,badtype,5000,0,,,,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is not None
    assert "must be 'mileage' or 'time'" in err


def test_csv_parse_bad_miles():
    """Test CSV with non-integer miles returns error."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "Oil Change,mileage,abc,0,,,,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is not None
    assert "integer" in err


def test_csv_parse_missing_required_columns():
    """Test CSV with explicit header missing required columns returns error."""
    csv_text = "name,interval_miles\nOil Change,5000"
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is not None
    assert "'name' and 'type'" in err


def test_csv_parse_defaults():
    """Test CSV uses defaults for empty optional fields."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "Oil Change,mileage,,,,,,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is None
    assert intervals[0]["interval_miles"] == 5000
    assert intervals[0]["last_serviced_mileage"] == 0


def test_csv_recurring_false():
    """Test CSV recurring=false parses correctly."""
    csv_text = (
        "name,type,interval_miles,last_serviced_mileage,"
        "interval_value,period,recurring,last_serviced_date\n"
        "One-time check,time,,,30,days,false,"
    )
    intervals, err = _parse_csv_intervals(csv_text)
    assert err is None
    assert intervals[0]["recurring"] is False


# --- Migration tests ---


def test_migrate_adds_type_field():
    """Test migration backfills type field on legacy intervals."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.options = {
        "units": "imperial",
        "update_interval": 5,
        "service_intervals": [
            {"name": "Oil Change", "interval_miles": 5000,
             "last_serviced_mileage": 0},
        ],
    }

    _migrate_service_intervals(mock_hass, mock_entry)

    mock_hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = (
        mock_hass.config_entries.async_update_entry.call_args
    )
    new_options = call_kwargs[1]["options"]
    assert new_options["service_intervals"][0]["type"] == "mileage"


def test_migrate_skips_already_typed():
    """Test migration does not update intervals that already have type."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.options = {
        "units": "imperial",
        "update_interval": 5,
        "service_intervals": [
            {"name": "Oil Change", "type": "mileage",
             "interval_miles": 5000, "last_serviced_mileage": 0},
        ],
    }

    _migrate_service_intervals(mock_hass, mock_entry)

    mock_hass.config_entries.async_update_entry.assert_not_called()


def test_migrate_no_intervals():
    """Test migration is a no-op when no intervals exist."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.options = {
        "units": "imperial",
        "update_interval": 5,
        "service_intervals": [],
    }

    _migrate_service_intervals(mock_hass, mock_entry)

    mock_hass.config_entries.async_update_entry.assert_not_called()
