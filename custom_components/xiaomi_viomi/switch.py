"""Switches of the Xiaomi Viomi vacuum."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ViomiConfigEntry, ViomiCoordinator
from .entity import ViomiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViomiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Viomi switches from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        [ViomiRepeatSwitch(coordinator), ViomiDoNotDisturbSwitch(coordinator)]
    )


class ViomiRepeatSwitch(ViomiEntity, SwitchEntity):
    """Clean everything twice."""

    _attr_translation_key = "repeat_cleaning"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_unique_id}_repeat_cleaning"

    @property
    def is_on(self) -> bool:
        """Return whether cleaning is repeated."""
        return bool(self.coordinator.data.status.repeat_cleaning)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn repeat cleaning on."""
        await self._try_command(
            "Unable to set repeat cleaning: %s",
            self.coordinator.device.set_repeat,
            True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn repeat cleaning off."""
        await self._try_command(
            "Unable to set repeat cleaning: %s",
            self.coordinator.device.set_repeat,
            False,
        )


class ViomiDoNotDisturbSwitch(ViomiEntity, SwitchEntity):
    """Do not disturb, keeping the hours set on the robot."""

    _attr_translation_key = "do_not_disturb"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_unique_id}_do_not_disturb"

    @property
    def is_on(self) -> bool:
        """Return whether do not disturb is enabled."""
        return self.coordinator.data.dnd.enabled

    async def _set(self, disable: bool) -> None:
        dnd = self.coordinator.data.dnd
        await self._try_command(
            "Unable to set do not disturb: %s",
            self.coordinator.device.set_dnd,
            disable,
            dnd.start.hour,
            dnd.start.minute,
            dnd.end.hour,
            dnd.end.minute,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable do not disturb."""
        await self._set(False)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable do not disturb."""
        await self._set(True)
