"""Vacuum platform of the Xiaomi Viomi integration."""

import logging
from collections.abc import Callable
from functools import partial
from typing import Any

import probatio
from homeassistant.components.vacuum import (
    ATTR_CLEANED_AREA,
    StateVacuumEntity,
    VacuumActivity,
)
from homeassistant.components.vacuum import (
    PLATFORM_SCHEMA as VACUUM_PLATFORM_SCHEMA,
)
from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_TOKEN,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddConfigEntryEntitiesCallback,
    AddEntitiesCallback,
)
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from miio import DeviceException
from miio.integrations.vacuum.viomi.viomivacuum import ViomiVacuumSpeed

from .const import (
    ATTR_CLEANING_TIME,
    ATTR_DO_NOT_DISTURB,
    ATTR_DO_NOT_DISTURB_END,
    ATTR_DO_NOT_DISTURB_START,
    ATTR_ERROR,
    ATTR_FILTER_LEFT,
    ATTR_MAIN_BRUSH_LEFT,
    ATTR_MOP_ATTACHED,
    ATTR_MOP_LEFT,
    ATTR_SIDE_BRUSH_LEFT,
    ATTR_STATUS,
    DOMAIN,
    ERRORS_FALSE_POSITIVE,
    STATE_CODE_TO_ACTIVITY,
    SUPPORT_VIOMI,
)
from .coordinator import ViomiConfigEntry, ViomiCoordinator
from .entity import ViomiEntity

_LOGGER = logging.getLogger(__name__)

FAN_SPEEDS = {speed.name: speed.value for speed in ViomiVacuumSpeed}

PLATFORM_SCHEMA = VACUUM_PLATFORM_SCHEMA.extend(
    {
        probatio.Optional(CONF_NAME): cv.string,
        probatio.Required(CONF_TOKEN): cv.string,
        probatio.Required(CONF_HOST): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import the legacy YAML configuration into a config entry."""
    import_data = {
        key: config[key] for key in (CONF_HOST, CONF_TOKEN, CONF_NAME) if key in config
    }
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=import_data
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViomiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Viomi vacuum from a config entry."""
    async_add_entities([ViomiVacuumEntity(entry.runtime_data)])


class ViomiVacuumEntity(ViomiEntity, StateVacuumEntity):
    """Xiaomi Viomi vacuum."""

    _attr_name = None
    _attr_supported_features = SUPPORT_VIOMI
    _attr_fan_speed_list = list(FAN_SPEEDS)

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the vacuum."""
        super().__init__(coordinator)
        self._attr_unique_id = self._device_unique_id

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the activity of the vacuum cleaner."""
        # The vacuum reverts back to an idle state after erroring out.
        # We want to keep returning an error until it has been cleared.
        if self._got_error():
            return VacuumActivity.ERROR

        return STATE_CODE_TO_ACTIVITY.get(int(self.coordinator.data.status.state.value))

    @property
    def fan_speed(self) -> str | None:
        """Return the fan speed of the vacuum cleaner."""
        try:
            return self.coordinator.data.status.fanspeed.name
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the specific state attributes of this vacuum cleaner."""
        data = self.coordinator.data
        attrs = {
            ATTR_DO_NOT_DISTURB: STATE_ON if data.dnd.enabled else STATE_OFF,
            ATTR_DO_NOT_DISTURB_START: str(data.dnd.start),
            ATTR_DO_NOT_DISTURB_END: str(data.dnd.end),
            ATTR_CLEANING_TIME: int(data.status.clean_time.total_seconds() / 60),
            ATTR_CLEANED_AREA: int(data.status.clean_area),
            ATTR_MAIN_BRUSH_LEFT: int(
                data.consumables.main_brush_left.total_seconds() / 3600
            ),
            ATTR_SIDE_BRUSH_LEFT: int(
                data.consumables.side_brush_left.total_seconds() / 3600
            ),
            ATTR_MOP_LEFT: int(data.consumables.mop_left.total_seconds() / 3600),
            ATTR_FILTER_LEFT: int(data.consumables.filter_left.total_seconds() / 3600),
            ATTR_STATUS: self.activity,
            ATTR_MOP_ATTACHED: data.status.mop_installed,
        }

        if self._got_error():
            attrs[ATTR_ERROR] = data.status.error
        return attrs

    def _got_error(self) -> bool:
        error_code = self.coordinator.data.status.error_code
        return bool(error_code and error_code not in ERRORS_FALSE_POSITIVE)

    async def _try_command(
        self, mask_error: str, func: Callable[..., Any], *args: Any
    ) -> bool:
        """Call a vacuum command handling error messages."""
        try:
            await self.hass.async_add_executor_job(partial(func, *args))
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

        await self.coordinator.async_request_refresh()
        return True

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        await self._try_command(
            "Unable to start the vacuum: %s", self.coordinator.device.start
        )

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        await self._try_command(
            "Unable to set start/pause: %s", self.coordinator.device.pause
        )

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        await self._try_command("Unable to stop: %s", self.coordinator.device.stop)

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        await self._try_command("Unable to locate: %s", self.coordinator.device.locate)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed."""
        try:
            if fan_speed in FAN_SPEEDS:
                speed = ViomiVacuumSpeed(FAN_SPEEDS[fan_speed])
            else:
                speed = ViomiVacuumSpeed(int(fan_speed))
        except ValueError as exc:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_fan_speed",
                translation_placeholders={
                    "fan_speed": fan_speed,
                    "valid_speeds": ", ".join(self.fan_speed_list),
                },
            ) from exc

        await self._try_command(
            "Unable to set fan speed: %s", self.coordinator.device.set_fan_speed, speed
        )

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self._try_command(
            "Unable to return home: %s", self.coordinator.device.home
        )

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send raw command."""
        await self._try_command(
            "Unable to send command to the vacuum: %s",
            self.coordinator.device.raw_command,
            command,
            params,
        )
