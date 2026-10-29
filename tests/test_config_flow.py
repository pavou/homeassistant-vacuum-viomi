"""Test the Xiaomi Viomi integration config flow."""

from unittest.mock import patch

import pytest
from construct.core import ChecksumError
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from miio import DeviceException
from miio.integrations.vacuum.viomi.viomivacuum import ViomiVacuum

from custom_components.xiaomi_viomi.const import DOMAIN
from tests import (
    TEST_HOST,
    TEST_MAC,
    TEST_MODEL,
    TEST_NAME,
    TEST_TOKEN,
    get_mocked_entry,
    mocked_viomi_device,
)

USER_INPUT = {"host": TEST_HOST, "token": TEST_TOKEN, "name": TEST_NAME}


async def _start_user_flow(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form and create the entry."""
    flow_result = await _start_user_flow(hass)

    assert flow_result["type"] is FlowResultType.FORM
    assert not flow_result["errors"]

    with (
        mocked_viomi_device(),
        patch(
            "custom_components.xiaomi_viomi.async_setup_entry", return_value=True
        ) as mock_setup_entry,
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_result["flow_id"], USER_INPUT
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["data"] == {
        "host": TEST_HOST,
        "name": TEST_NAME,
        "token": TEST_TOKEN,
        "model": TEST_MODEL,
        "mac": TEST_MAC,
    }
    assert result["result"].unique_id == TEST_MAC
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (DeviceException("timeout"), "cannot_connect"),
        (ValueError, "unknown"),
    ],
)
async def test_form_errors(hass: HomeAssistant, exception, error) -> None:
    """Test the errors are reported on the form."""
    flow_result = await _start_user_flow(hass)

    with patch.object(ViomiVacuum, "info", side_effect=exception):
        result = await hass.config_entries.flow.async_configure(
            flow_result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """A wrong token shows up as a checksum error."""
    flow_result = await _start_user_flow(hass)

    exception = DeviceException("bad token")
    exception.__cause__ = ChecksumError("checksum mismatch")

    with patch.object(ViomiVacuum, "info", side_effect=exception):
        result = await hass.config_entries.flow.async_configure(
            flow_result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_already_configured_updates_the_entry(hass: HomeAssistant) -> None:
    """A known device is updated instead of being added twice."""
    entry = get_mocked_entry()
    entry.add_to_hass(hass)

    flow_result = await _start_user_flow(hass)

    with (
        mocked_viomi_device(),
        patch("custom_components.xiaomi_viomi.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            flow_result["flow_id"], {**USER_INPUT, "host": "2.2.2.2"}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data["host"] == "2.2.2.2"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_import(hass: HomeAssistant) -> None:
    """The legacy YAML platform is imported."""
    with (
        mocked_viomi_device(),
        patch("custom_components.xiaomi_viomi.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={"host": TEST_HOST, "token": TEST_TOKEN},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_MODEL
    assert result["data"]["mac"] == TEST_MAC


async def test_import_cannot_connect(hass: HomeAssistant) -> None:
    with patch.object(ViomiVacuum, "info", side_effect=DeviceException("timeout")):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={"host": TEST_HOST, "token": TEST_TOKEN},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cannot_connect"


async def _start_options_flow(hass: HomeAssistant, options: dict | None = None):
    entry = get_mocked_entry(options)
    with mocked_viomi_device():
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return entry, result


async def test_options_flow_sets_the_rooms(hass: HomeAssistant) -> None:
    entry, result = await _start_options_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with mocked_viomi_device():
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"rooms": ["10", "011", "25"]}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        "rooms": {"10": "Room 10", "11": "Room 11", "25": "Room 25"}
    }


@pytest.mark.parametrize("room_ids", [["x"], ["10", "-1"], ["1.5"]])
async def test_options_flow_rejects_bad_rooms(hass: HomeAssistant, room_ids) -> None:
    _, result = await _start_options_flow(hass)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"rooms": room_ids}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"rooms": "invalid_rooms"}


async def test_options_flow_keeps_names_and_clears_the_rooms(
    hass: HomeAssistant,
) -> None:
    entry, result = await _start_options_flow(
        hass, {"rooms": {"10": "Kitchen", "11": "Hall"}}
    )
    (key,) = result["data_schema"].schema
    assert key.description == {"suggested_value": ["10", "11"]}

    with mocked_viomi_device():
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"rooms": ["10", "12"]}
        )
        await hass.async_block_till_done()

    assert entry.options == {"rooms": {"10": "Kitchen", "12": "Room 12"}}

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with mocked_viomi_device():
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"rooms": []}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {}
