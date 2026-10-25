# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (HACS, domain `xiaomi_viomi`) for Viomi / Mijia vacuum robots (`viomi.vacuum.v6/v7/v8`). It is a fork of `nergal/homeassistant-vacuum-viomi` (our `origin` is `pavou/...`). Targets Home Assistant Core 2026.10.4 and `python-miio` 0.5.12 (0.1.0, modernized from upstream 0.0.4). The device protocol has not been tested against real hardware since the update, so the tests that assert the `send()` calls are the safety net.

## Commands

Tooling is `uv` + `ruff` + `mypy` (Python >= 3.14.2, which HA 2026.10 requires). The Makefile wraps `uv run`:

- `uv sync` — create `.venv` and install everything
- `make lint` — `ruff check`, `ruff format --check`, `mypy`; `make lintfix` auto-fixes and formats
- `make test` — pytest; `make coverage` writes `coverage.xml` (what CI runs)
- Single test: `uv run pytest tests/test_vacuum.py::test_name`

Home Assistant core imports `fcntl`, so **the tests cannot run on native Windows**; use WSL/Linux, and there set `UV_PROJECT_ENVIRONMENT` to a path outside the repo (e.g. `$HOME/viomi-ci-venv`) so `uv run` does not recreate the Windows `.venv`. `netifaces` (an optional `python-miio` dependency used only by its firmware updater) does not build on Python 3.14, so `pyproject.toml` overrides it away; the real HA install is unaffected.

CI (`.github/workflows/workflow.yaml`) runs lint + coverage, CodeQL, hassfest and HACS validation.

## Architecture

All code is in `custom_components/xiaomi_viomi/`. The pieces only make sense together:

- **One poller, many entities.** `__init__.async_setup_entry` builds a `ViomiCoordinator` (coordinator.py), does the first refresh, stores it in `entry.runtime_data`, and forwards to the `vacuum` and `sensor` platforms. The coordinator fetches status, consumables and DND in one executor call; entities read `coordinator.data` and never talk to the device to read state.
- **Entities derive from `ViomiEntity` (entity.py)**, not from core's `xiaomi_miio` (which is no longer a dependency). Entity unique ids come from the config entry's unique id (the device MAC) and must stay stable so existing users keep their entities: the vacuum uses it as is, the battery sensor appends `_battery`. The vacuum entity no longer exposes battery (core removed it from `StateVacuumEntity`), hence the separate battery sensor.
- **Protocol quirks to preserve.** `ViomiCoordinator._fetch` bypasses miio's `status()` by calling `get_prop` once per name in `const.DEVICE_PROPERTIES`. `PatchedViomiVacuum` adds `locate` (`set_resetpos [1]`), which `python-miio` lacks. State codes map via `const.STATE_CODE_TO_ACTIVITY`; `ERRORS_FALSE_POSITIVE` lists `err_state` values that are not real errors, and a real error keeps the activity at `ERROR` until cleared. Property names such as `battary_life` are the device's real (misspelled) names.
- **Config flow** (`config_flow.py`): `validate_input` is shared by the user step and the import step. The MAC is the unique id; re-adding a known device updates host/token/name/model and reloads it. A `ChecksumError` cause means a wrong token (`invalid_auth`), any other `DeviceException` is `cannot_connect`.
- **YAML is deprecated.** `vacuum.async_setup_platform` only starts an import flow and raises a repair issue (`deprecated_yaml`); there is no YAML-only setup path anymore.
- **0.0.3 migration shim** in `__init__.async_setup_entry` backfills name/model for entries without `model`. Covered by `test_setup_with_update_to_004`; keep it working.
- Core now uses `probatio` instead of `voluptuous` for schemas; follow core.

## Tests

`tests/__init__.py` provides `mocked_viomi_device()`, which patches `ViomiVacuum.send` to fake `get_prop`, `get_consumables`, `get_notdisturb` and `miIO.info`. Nothing touches the network, and tests assert the exact `send()` calls. `conftest.py` auto-enables custom integrations via `pytest-homeassistant-custom-component`, whose version pins the Home Assistant version under test (`0.13.375` = `2026.10.4`). New device properties must be added to `MOCKED_DEVICE_STATE`.

## Keeping in sync

`manifest.json` requirements must equal the pins of core's own `xiaomi_miio` integration (`python-miio`, `construct`), otherwise HA's requirement installer conflicts with it. Mirror them in `pyproject.toml`.
