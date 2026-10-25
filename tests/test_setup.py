"""Tests for the setup of the Xiaomi Viomi integration."""

from unittest.mock import patch

from homeassistant.components.vacuum import DOMAIN, VacuumActivity
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from miio import DeviceException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.xiaomi_viomi.const import DOMAIN as CUSTOM_DOMAIN
from tests import (
    MOCKING_SEND_METHOD,
    TEST_HOST,
    TEST_MAC,
    TEST_MODEL,
    TEST_NAME,
    TEST_TOKEN,
    get_entity_id,
    get_mocked_entry,
    mocked_viomi_device,
)


async def test_config_entry_setup_and_unload(hass: HomeAssistant):
    entry = get_mocked_entry()

    with mocked_viomi_device():
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        state = hass.states.get(get_entity_id())
        assert state
        assert state.state == VacuumActivity.DOCKED

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_when_device_is_unreachable(hass: HomeAssistant):
    entry = get_mocked_entry()

    with patch(MOCKING_SEND_METHOD, side_effect=DeviceException("timeout")):
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_yaml_platform_is_imported(hass: HomeAssistant):
    config = {
        DOMAIN: [
            {
                "platform": CUSTOM_DOMAIN,
                "host": TEST_HOST,
                "token": TEST_TOKEN,
                "name": TEST_NAME,
            }
        ]
    }

    with mocked_viomi_device():
        await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

        entries = hass.config_entries.async_entries(CUSTOM_DOMAIN)
        assert len(entries) == 1
        assert entries[0].unique_id == TEST_MAC
        assert entries[0].title == TEST_NAME

        state = hass.states.get(get_entity_id())
        assert state
        assert state.state == VacuumActivity.DOCKED
        assert state.name == TEST_NAME

    issue = ir.async_get(hass).async_get_issue(CUSTOM_DOMAIN, "deprecated_yaml")
    assert issue is not None


async def test_yaml_platform_without_name_uses_the_model(hass: HomeAssistant):
    config = {
        DOMAIN: [
            {
                "platform": CUSTOM_DOMAIN,
                "host": TEST_HOST,
                "token": TEST_TOKEN,
            }
        ]
    }

    with mocked_viomi_device():
        await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

        state = hass.states.get(get_entity_id(True))
        assert state
        assert state.name == TEST_MODEL


async def test_setup_with_update_to_004(hass: HomeAssistant):
    """Entries created by 0.0.3 have no name and model stored."""
    entry = MockConfigEntry(
        domain=CUSTOM_DOMAIN,
        title=TEST_NAME,
        unique_id=TEST_MAC,
        data={
            "host": TEST_HOST,
            "token": TEST_TOKEN,
            "mac": TEST_MAC,
        },
    )

    with mocked_viomi_device():
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.data["name"] == TEST_NAME
        assert entry.data["model"] == TEST_NAME

        state = hass.states.get(get_entity_id())
        assert state
        assert state.name == TEST_NAME


async def test_yaml_platform_that_cannot_connect_raises_no_issue(hass: HomeAssistant):
    config = {
        DOMAIN: [{"platform": CUSTOM_DOMAIN, "host": TEST_HOST, "token": TEST_TOKEN}]
    }

    with patch(MOCKING_SEND_METHOD, side_effect=DeviceException("timeout")):
        await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

    assert not hass.config_entries.async_entries(CUSTOM_DOMAIN)
    assert ir.async_get(hass).async_get_issue(CUSTOM_DOMAIN, "deprecated_yaml") is None
