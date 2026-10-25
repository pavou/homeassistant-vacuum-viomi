"""Config flow to configure Xiaomi Viomi."""

import logging
from typing import Any

import probatio
from construct.core import ChecksumError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_MODEL,
    CONF_NAME,
    CONF_TOKEN,
    DEVICE_DEFAULT_NAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device_registry import format_mac
from miio import DeviceException
from miio.integrations.vacuum.viomi.viomivacuum import ViomiVacuum

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEVICE_CONFIG = probatio.Schema(
    {
        probatio.Required(CONF_HOST): str,
        probatio.Required(CONF_TOKEN): probatio.All(
            str, probatio.Length(min=32, max=32)
        ),
        probatio.Optional(CONF_NAME, default=DEVICE_DEFAULT_NAME): str,
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Connect to the device and return the data of the config entry."""
    device = ViomiVacuum(data[CONF_HOST], data[CONF_TOKEN])

    try:
        info = await hass.async_add_executor_job(device.info)
    except DeviceException as error:
        if isinstance(error.__cause__, ChecksumError):
            raise InvalidAuth from error

        _LOGGER.debug("Cannot connect to the Viomi device %s", data[CONF_HOST])
        raise CannotConnect from error

    return {
        CONF_HOST: data[CONF_HOST],
        CONF_TOKEN: data[CONF_TOKEN],
        CONF_MODEL: info.model,
        CONF_NAME: data.get(CONF_NAME) or info.model,
        CONF_MAC: format_mac(info.mac_address),
    }


class XiaomiViomiFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Xiaomi Viomi config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return await self._async_create_or_update_entry(info)

        return self.async_show_form(
            step_id="user", data_schema=DEVICE_CONFIG, errors=errors
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import the configuration of the legacy YAML platform."""
        try:
            info = await validate_input(self.hass, import_data)
        except CannotConnect:
            _LOGGER.error(
                "Cannot import the YAML configuration of %s, check the host",
                import_data[CONF_HOST],
            )
            return self.async_abort(reason="cannot_connect")
        except InvalidAuth:
            _LOGGER.error(
                "Cannot import the YAML configuration of %s, check the token",
                import_data[CONF_HOST],
            )
            return self.async_abort(reason="invalid_auth")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected exception")
            return self.async_abort(reason="unknown")

        # Only tell the user to remove the YAML once it has been imported.
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            "deprecated_yaml",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
        )
        return await self._async_create_or_update_entry(info)

    async def _async_create_or_update_entry(
        self, info: dict[str, Any]
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(info[CONF_MAC], raise_on_progress=False)
        # A known device gets the new host, token, name and model, and is reloaded.
        self._abort_if_unique_id_configured(updates=info)

        return self.async_create_entry(title=info[CONF_NAME], data=info)
