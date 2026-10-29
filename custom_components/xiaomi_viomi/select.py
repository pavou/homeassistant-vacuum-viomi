"""Selects of the Xiaomi Viomi vacuum."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from miio.integrations.vacuum.viomi.viomivacuum import ViomiMode

from .coordinator import ViomiConfigEntry, ViomiCoordinator
from .entity import ViomiEntity

# CleanZone and CleanSpot are states the robot enters, not modes to select.
CLEAN_MODES = {
    "vacuum": ViomiMode.Vacuum,
    "vacuum_and_mop": ViomiMode.VacuumAndMop,
    "mop": ViomiMode.Mop,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViomiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Viomi selects from a config entry."""
    async_add_entities([ViomiCleanModeSelect(entry.runtime_data)])


class ViomiCleanModeSelect(ViomiEntity, SelectEntity):
    """Whether the robot vacuums, mops or both."""

    _attr_translation_key = "clean_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(CLEAN_MODES)

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_unique_id}_clean_mode"

    @property
    def current_option(self) -> str | None:
        """Return the current clean mode."""
        mode = self.coordinator.data.status.mop_mode
        return next((key for key, value in CLEAN_MODES.items() if value == mode), None)

    async def async_select_option(self, option: str) -> None:
        """Change the clean mode."""
        await self._try_command(
            "Unable to set the clean mode: %s",
            self.coordinator.device.clean_mode,
            CLEAN_MODES[option],
        )
