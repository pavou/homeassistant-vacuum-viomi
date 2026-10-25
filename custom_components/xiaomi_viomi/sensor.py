"""Sensors of the Xiaomi Viomi vacuum."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ViomiConfigEntry, ViomiCoordinator
from .entity import ViomiEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViomiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Viomi sensors from a config entry."""
    async_add_entities([ViomiBatterySensor(entry.runtime_data)])


class ViomiBatterySensor(ViomiEntity, SensorEntity):
    """Battery level of the vacuum."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_unique_id}_battery"

    @property
    def native_value(self) -> int:
        """Return the battery level."""
        return self.coordinator.data.status.battery
