# ha-drone-mobile

[![CI](https://github.com/HolyBitsLLC/ha-drone-mobile/actions/workflows/ci.yaml/badge.svg)](https://github.com/HolyBitsLLC/ha-drone-mobile/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)

Home Assistant custom integration for [DroneMobile](https://www.dronemobile.com/) remote start systems (Firstech / Compustar).

## Disclaimer

This integration uses an unofficial, unsupported API from DroneMobile. It is subject to change without notice. The authors claim no responsibility for damages to your vehicle from use of this integration.

## Features

- **Remote Start / Stop** — start and stop your vehicle engine
- **Lock / Unlock** — control door locks
- **Trunk Release** — pop the trunk
- **Panic Alarm** — activate / deactivate panic
- **Auxiliary Outputs** — trigger Aux1 and Aux2
- **GPS Tracking** — vehicle location on the HA map
- **Sensors** — battery voltage, battery %, odometer, fuel level, interior/exterior temperature, last update time
- **Binary Sensors** — engine running state, lock state
- **Imperial / Metric** — configurable unit system
- **Config Flow** — full UI-based setup with vehicle selection

## Requirements

- Home Assistant 2024.1.0 or newer
- A DroneMobile account with an active subscription
- A vehicle with a DroneMobile-compatible remote start system installed

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `HolyBitsLLC/ha-drone-mobile` with category **Integration**
4. Search for "DroneMobile" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/drone_mobile` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **DroneMobile**
3. Enter your DroneMobile email and password
4. Select your vehicle
5. Configure unit system and update interval in integration options

## Entities

### Sensors
| Entity | Description |
|--------|-------------|
| Battery Voltage | Vehicle battery voltage (V) |
| Battery | Battery percentage (%) |
| Odometer | Distance traveled (mi/km) |
| Fuel Level | Fuel level percentage (%) |
| Interior Temperature | Interior temp (°F/°C) |
| Exterior Temperature | Exterior temp (°F/°C) |
| Last Updated | Last data update timestamp |

### Binary Sensors
| Entity | Description |
|--------|-------------|
| Engine | Whether the engine is running |
| Locked | Whether doors are unlocked (problem state) |

### Switches
| Entity | Description |
|--------|-------------|
| Remote Start | Start/stop the engine |
| Panic | Activate/deactivate panic alarm |
| Trunk | Pop the trunk (momentary) |
| Auxiliary 1 | Trigger Aux1 (momentary) |
| Auxiliary 2 | Trigger Aux2 (momentary) |

### Lock
| Entity | Description |
|--------|-------------|
| Door Lock | Lock/unlock vehicle doors |

### Device Tracker
| Entity | Description |
|--------|-------------|
| Location | Vehicle GPS position on map |

## Development

```bash
# Clone
git clone git@github.com:HolyBitsLLC/ha-drone-mobile.git
cd ha-drone-mobile

# Install dev dependencies
pip install -r requirements-dev.txt
pip install -e .

# Run tests
pytest --cov=custom_components/drone_mobile tests/

# Lint
ruff check custom_components/ tests/
```

## License

MIT — see [LICENSE](LICENSE).
