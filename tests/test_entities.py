"""Test the entities and room cleaning of the Xiaomi Viomi integration."""

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
)
from homeassistant.components.switch import (
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.components.vacuum import (
    DATA_COMPONENT,
    Segment,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant

from custom_components.xiaomi_viomi.const import SUPPORT_VIOMI
from tests import get_entity_id, get_mocked_entry, mocked_viomi_device

ROOMS = {"10": "Kitchen", "11": "Living room"}


def _state(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    assert state
    return state.state


async def _setup(hass: HomeAssistant, options: dict | None = None):
    entry = get_mocked_entry(options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _vacuum(hass: HomeAssistant):
    return hass.data[DATA_COMPONENT].get_entity(get_entity_id())


async def test_default_room_numbers_are_segments(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass)

        vacuum = _vacuum(hass)
        assert vacuum.supported_features == (
            SUPPORT_VIOMI | VacuumEntityFeature.CLEAN_AREA
        )
        assert await vacuum.async_get_segments() == [
            Segment(id=str(room_id), name=f"Room {room_id}")
            for room_id in range(10, 20)
        ]


async def test_configured_rooms_add_to_and_rename_the_defaults(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass, {"rooms": {**ROOMS, "25": "Attic"}})

        segments = await _vacuum(hass).async_get_segments()

        assert Segment(id="10", name="Kitchen") in segments
        assert Segment(id="11", name="Living room") in segments
        assert Segment(id="12", name="Room 12") in segments
        assert segments[-1] == Segment(id="25", name="Attic")
        assert len(segments) == 11


async def test_clean_rooms_sends_the_room_ids(hass: HomeAssistant):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass, {"rooms": ROOMS})
        mock_device_send.reset_mock()

        await _vacuum(hass).async_clean_segments(["10", "11"])

        mock_device_send.assert_any_call("set_mode_withroom", [0, 1, 2, 10, 11])


@pytest.mark.parametrize(
    ("option", "value"), [("vacuum", 0), ("vacuum_and_mop", 1), ("mop", 2)]
)
async def test_clean_mode_select(hass: HomeAssistant, option, value):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        entity_id = "select.mocked_vacuum_clean_mode"
        assert _state(hass, entity_id) == "vacuum"
        mock_device_send.reset_mock()

        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {"entity_id": entity_id, ATTR_OPTION: option},
            blocking=True,
        )

        mock_device_send.assert_any_call("set_mop", [value])


async def test_clean_mode_reports_mopping(hass: HomeAssistant):
    with mocked_viomi_device({"is_mop": 2}):
        await _setup(hass)

        assert _state(hass, "select.mocked_vacuum_clean_mode") == "mop"


@pytest.mark.parametrize(
    ("service", "value"), [(SERVICE_TURN_ON, 1), (SERVICE_TURN_OFF, 0)]
)
async def test_repeat_switch(hass: HomeAssistant, service, value):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        entity_id = "switch.mocked_vacuum_repeat_cleaning"
        assert _state(hass, entity_id) == "off"
        mock_device_send.reset_mock()

        await hass.services.async_call(
            SWITCH_DOMAIN, service, {"entity_id": entity_id}, blocking=True
        )

        mock_device_send.assert_any_call("set_repeat", [value])


@pytest.mark.parametrize(
    ("service", "enabled"), [(SERVICE_TURN_ON, 1), (SERVICE_TURN_OFF, 0)]
)
async def test_do_not_disturb_switch_keeps_the_hours(
    hass: HomeAssistant, service, enabled
):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        entity_id = "switch.mocked_vacuum_do_not_disturb"
        assert _state(hass, entity_id) == "off"
        mock_device_send.reset_mock()

        await hass.services.async_call(
            SWITCH_DOMAIN, service, {"entity_id": entity_id}, blocking=True
        )

        mock_device_send.assert_any_call("set_notdisturb", [enabled, 0, 0, 0, 0])


async def test_sensors(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass)

        assert _state(hass, "sensor.mocked_vacuum_cleaned_area") == "11.96"
        assert _state(hass, "sensor.mocked_vacuum_cleaning_time") == "20"
        assert _state(hass, "sensor.mocked_vacuum_main_brush_hours") == "0"
        assert _state(hass, "sensor.mocked_vacuum_filter_hours") == "0"
        assert _state(hass, "binary_sensor.mocked_vacuum_mop_attached") == "off"
        # 2105 (fully charged) is not a real error.
        assert _state(hass, "sensor.mocked_vacuum_error") == "unknown"


async def test_error_sensor_reports_a_real_error(hass: HomeAssistant):
    with mocked_viomi_device({"err_state": 502}):
        await _setup(hass)

        assert _state(hass, "sensor.mocked_vacuum_error") == "Low battery"


@pytest.mark.parametrize(
    ("name", "consumable"),
    [("main_brush", 1), ("side_brush", 2), ("filter", 3), ("mop", 4)],
)
async def test_reset_consumable_buttons(hass: HomeAssistant, name, consumable):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass)
        mock_device_send.reset_mock()

        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {"entity_id": f"button.mocked_vacuum_reset_{name}"},
            blocking=True,
        )

        mock_device_send.assert_any_call("set_consumables", [consumable])


async def test_consumable_sensors_report_the_worked_hours(hass: HomeAssistant):
    with mocked_viomi_device(consumables=[191, 150, 120, 64]):
        await _setup(hass)

        assert _state(hass, "sensor.mocked_vacuum_main_brush_hours") == "191"
        assert _state(hass, "sensor.mocked_vacuum_side_brush_hours") == "150"
        assert _state(hass, "sensor.mocked_vacuum_filter_hours") == "120"
        assert _state(hass, "sensor.mocked_vacuum_mop_hours") == "64"
