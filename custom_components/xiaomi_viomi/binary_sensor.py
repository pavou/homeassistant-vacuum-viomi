"""Binary sensors of the Xiaomi Viomi vacuum."""

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up the Xiaomi Viomi binary sensors from a config entry."""
    async_add_entities([ViomiMopAttachedSensor(entry.runtime_data)])


class ViomiMopAttachedSensor(ViomiEntity, BinarySensorEntity):
    """Whether the mop is attached."""

    _attr_translation_key = "mop_attached"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_unique_id}_mop_attached"

    @property
    def is_on(self) -> bool:
        """Return whether the mop is attached."""
        return self.coordinator.data.status.mop_installed
