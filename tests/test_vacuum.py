"""Test the Xiaomi Viomi vacuum platform."""

import pytest
from homeassistant.components.vacuum import (
    DOMAIN,
    SERVICE_LOCATE,
    SERVICE_PAUSE,
    SERVICE_RETURN_TO_BASE,
    SERVICE_SEND_COMMAND,
    SERVICE_SET_FAN_SPEED,
    SERVICE_START,
    SERVICE_STOP,
    VacuumActivity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from miio import DeviceException
from miio.integrations.vacuum.viomi.viomivacuum import ViomiVacuumSpeed

from custom_components.xiaomi_viomi.const import SUPPORT_VIOMI as SUPPORT_FEATURES
from tests import get_entity_id, get_mocked_entry, mocked_viomi_device


async def _setup(hass: HomeAssistant):
    entry = get_mocked_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_vacuum_state(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass)

        state = hass.states.get(get_entity_id())

        assert state
        assert state.state == VacuumActivity.DOCKED
        assert state.attributes["fan_speed"] == ViomiVacuumSpeed.Silent.name
        assert state.attributes["fan_speed_list"] == [
            "Silent",
            "Standard",
            "Medium",
            "Turbo",
        ]
        assert state.attributes["supported_features"] == SUPPORT_FEATURES
        assert state.attributes["status"] == "docked"
        assert "error" not in state.attributes


async def test_battery_sensor(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass)

        state = hass.states.get(
            get_entity_id().replace("vacuum.", "sensor.") + "_battery"
        )

        assert state
        assert state.state == "100"
        assert state.attributes["device_class"] == "battery"
        assert state.attributes["unit_of_measurement"] == "%"


test_service_data = [
    (SERVICE_START, "set_mode_withroom", [0, 1, 0]),
    (SERVICE_PAUSE, "set_mode", [0, 2]),
    (SERVICE_RETURN_TO_BASE, "set_charge", [1]),
    (SERVICE_LOCATE, "set_resetpos", [1]),
    (SERVICE_STOP, "set_mode", [0, 0]),
]


@pytest.mark.parametrize(("service", "method", "parameters"), test_service_data)
async def test_vacuum_service(hass: HomeAssistant, service, method, parameters):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        mock_device_send.reset_mock()

        await hass.services.async_call(
            DOMAIN, service, {"entity_id": get_entity_id()}, blocking=True
        )

        mock_device_send.assert_any_call(method, parameters)


async def test_vacuum_send_command_service(hass: HomeAssistant):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        mock_device_send.reset_mock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_COMMAND,
            {"command": "test_command", "entity_id": get_entity_id()},
            blocking=True,
        )

        mock_device_send.assert_any_call("test_command", None)


async def test_vacuum_command_refreshes_the_state(hass: HomeAssistant):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        mock_device_send.reset_mock()

        await hass.services.async_call(
            DOMAIN, SERVICE_STOP, {"entity_id": get_entity_id()}, blocking=True
        )
        await hass.async_block_till_done()

        mock_device_send.assert_any_call("get_prop", ["run_state"])


async def test_vacuum_failed_command_is_logged(hass: HomeAssistant, caplog):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)

        def fail(command, parameters=None):
            raise DeviceException("boom")

        mock_device_send.side_effect = fail

        await hass.services.async_call(
            DOMAIN, SERVICE_LOCATE, {"entity_id": get_entity_id()}, blocking=True
        )

        assert "Unable to locate" in caplog.text


@pytest.mark.parametrize(
    ("speed", "expected_value"),
    [
        #  numeric values
        ("0", ViomiVacuumSpeed.Silent.value),
        ("1", ViomiVacuumSpeed.Standard.value),
        ("2", ViomiVacuumSpeed.Medium.value),
        ("3", ViomiVacuumSpeed.Turbo.value),
        # string values
        ("Silent", ViomiVacuumSpeed.Silent.value),
        ("Standard", ViomiVacuumSpeed.Standard.value),
        ("Medium", ViomiVacuumSpeed.Medium.value),
        ("Turbo", ViomiVacuumSpeed.Turbo.value),
    ],
)
async def test_vacuum_fan_speed_service(
    hass: HomeAssistant, speed: str, expected_value: int
):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        mock_device_send.reset_mock()

        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_FAN_SPEED,
            {"entity_id": get_entity_id(), "fan_speed": speed},
            blocking=True,
        )

        mock_device_send.assert_any_call("set_suction", [expected_value])


@pytest.mark.parametrize("speed", ["-1", "9", "fast"])
async def test_vacuum_bad_fan_speed(hass: HomeAssistant, speed: str):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        mock_device_send.reset_mock()

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                SERVICE_SET_FAN_SPEED,
                {"entity_id": get_entity_id(), "fan_speed": speed},
                blocking=True,
            )

        assert "set_suction" not in [c.args[0] for c in mock_device_send.call_args_list]


@pytest.mark.parametrize(
    ("state_code", "activity"),
    [
        (3, VacuumActivity.CLEANING),
        (4, VacuumActivity.RETURNING),
        (5, VacuumActivity.DOCKED),
        (6, VacuumActivity.CLEANING),
        (9000, None),
    ],
)
async def test_vacuum_regular_state(hass: HomeAssistant, state_code, activity):
    with mocked_viomi_device({"run_state": state_code}):
        await _setup(hass)

        state = hass.states.get(get_entity_id())

        assert state
        assert state.attributes["status"] == activity


@pytest.mark.parametrize(
    ("error_code", "error_value"),
    [
        (502, "Low battery"),
        (9000, "Unknown error 9000"),
    ],
)
async def test_vacuum_error_state(hass: HomeAssistant, error_code, error_value):
    with mocked_viomi_device({"err_state": error_code}):
        await _setup(hass)

        state = hass.states.get(get_entity_id())

        assert state
        assert state.state == VacuumActivity.ERROR
        assert state.attributes["error"] == error_value
