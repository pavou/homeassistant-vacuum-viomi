"""Test room cleaning of the Xiaomi Viomi integration."""

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


async def test_no_room_cleaning_without_rooms(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass)

        assert _vacuum(hass).supported_features == SUPPORT_VIOMI
        assert await _vacuum(hass).async_get_segments() == []


async def test_rooms_are_segments(hass: HomeAssistant):
    with mocked_viomi_device():
        await _setup(hass, {"rooms": ROOMS})

        vacuum = _vacuum(hass)
        assert vacuum.supported_features == (
            SUPPORT_VIOMI | VacuumEntityFeature.CLEAN_AREA
        )
        assert await vacuum.async_get_segments() == [
            Segment(id="10", name="Kitchen"),
            Segment(id="11", name="Living room"),
        ]


async def test_clean_rooms_sends_the_room_ids(hass: HomeAssistant):
    with mocked_viomi_device() as mock_device_send:
        await _setup(hass, {"rooms": ROOMS})
        mock_device_send.reset_mock()

        await _vacuum(hass).async_clean_segments(["10", "11"])

        mock_device_send.assert_any_call("set_mode_withroom", [0, 1, 2, 10, 11])
