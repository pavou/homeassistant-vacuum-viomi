"""Buttons of the Xiaomi Viomi vacuum."""

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ViomiConfigEntry, ViomiCoordinator
from .entity import ViomiEntity


@dataclass(frozen=True, kw_only=True)
class ViomiButtonDescription(ButtonEntityDescription):
    """Describes a button that zeroes the worked hours of a consumable."""

    consumable: int


BUTTONS = (
    ViomiButtonDescription(
        key="reset_main_brush",
        translation_key="reset_main_brush",
        entity_category=EntityCategory.CONFIG,
        consumable=1,
    ),
    ViomiButtonDescription(
        key="reset_side_brush",
        translation_key="reset_side_brush",
        entity_category=EntityCategory.CONFIG,
        consumable=2,
    ),
    ViomiButtonDescription(
        key="reset_filter",
        translation_key="reset_filter",
        entity_category=EntityCategory.CONFIG,
        consumable=3,
    ),
    ViomiButtonDescription(
        key="reset_mop",
        translation_key="reset_mop",
        entity_category=EntityCategory.CONFIG,
        consumable=4,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViomiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Viomi buttons from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(ViomiResetButton(coordinator, desc) for desc in BUTTONS)


class ViomiResetButton(ViomiEntity, ButtonEntity):
    """Tell the robot that a consumable was replaced."""

    entity_description: ViomiButtonDescription

    def __init__(
        self, coordinator: ViomiCoordinator, description: ViomiButtonDescription
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self._device_unique_id}_{description.key}"

    async def async_press(self) -> None:
        """Reset the worked hours of the consumable."""
        await self._try_command(
            "Unable to reset the consumable: %s",
            self.coordinator.device.reset_consumable,
            self.entity_description.consumable,
        )
