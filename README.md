# Homeassistant Vacuum Viomi integration for HACS

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![codecov](https://codecov.io/gh/nergal/homeassistant-vacuum-viomi/branch/master/graph/badge.svg?token=MUHLPCJY2G)](https://codecov.io/gh/nergal/homeassistant-vacuum-viomi)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)
![GitHub](https://img.shields.io/github/license/nergal/homeassistant-vacuum-viomi)
[![Validation flow](https://github.com/nergal/homeassistant-vacuum-viomi/actions/workflows/workflow.yaml/badge.svg)](https://github.com/nergal/homeassistant-vacuum-viomi/actions/workflows/workflow.yaml)


Xiaomi Viomi vacuum robot integration for Home Assistant.

> :warning: **DISCLAIMER:** This code is an early alpha release with all related consequences. If you decide to use it, any feedback is appreciated

## Installation
### HACS
Install it through HACS by adding this as a custom repository: https://github.com/nergal/homeassistant-vacuum-viomi, go to the integrations page in your configuration, click on the `Add Integration` button in the bottom right corner of a screen, and search for `Xiaomi Viomi Vacuum`.

### Manual
Copy contents of `custom_components` folder to your Home Assistant `config/custom_components` folder. Restart Home Assistant, and then the integration can be added and configured through the native integration setup. If you don't see it in the native integrations list, press Ctrl+F5 to refresh the browser while you're on that page and retry.

Requires Home Assistant 2026.10.4 or newer.

### YAML (deprecated)
The `configuration.yaml` platform is still accepted, but it is only imported into a regular config entry on startup and a repair issue asks you to remove it. Prefer the UI. Existing YAML example:

```yaml
vacuum:
  - platform: xiaomi_viomi
    host: 192.168.1.1
    token: !secret vacuum
    name: Vacuum V8
```

## Upgrading from 0.0.4
Version 0.1.0 follows the changes of Home Assistant core, which break a few things:

* The battery level is no longer an attribute (`battery_level`) of the vacuum. Use the new `sensor.<name>_battery` entity.
* The `vacuum.turn_on`, `vacuum.turn_off`, `vacuum.toggle` and `vacuum.start_pause` services no longer exist in Home Assistant. Use `vacuum.start`, `vacuum.pause`, `vacuum.stop` and `vacuum.return_to_base`.
* The `vacuum.clean_spot` service is not supported (the device never supported it).
* YAML configuration is only imported into a config entry.

Existing config entries keep their entity IDs.

## Tested models
| Model | Device ID | Aliases | Status |
| ----- | --------- | ------- | ------ |
| **STYJ02YM** | viomi.vacuum.v8 | Mi Robot Vacuum-Mop P <br> MiJia Mi Robot Vacuum Cleaner <br> Xiaomi Mijia Robot Vacuum Cleaner LDS | :white_check_mark: Verified |
| **STY02YM** | viomi.vacuum.v7 | Mi Robot Vacuum-Mop P (CN) | :white_check_mark: Verified |
| **V-RVCLM21B** | viomi.vacuum.v6 | Viomi V2 <br> Xiaomi Viomi Cleaning Robot <br> Viomi Cleaning Robot V2 Pro | :warning: Not tested |

## Disclaimer
This project is not affiliated, associated, authorized, endorsed by, or in any way officially connected with the Xiaomi Corporation,
or any of its subsidiaries or its affiliates. The official Xiaomi website can be found at https://www.mi.com/global/.

## License
This project is under the MIT license.
