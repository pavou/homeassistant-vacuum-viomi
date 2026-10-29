"""Sensors of the Xiaomi Viomi vacuum."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfArea, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import ERRORS_FALSE_POSITIVE
from .coordinator import ViomiConfigEntry, ViomiCoordinator, ViomiData
from .entity import ViomiEntity


@dataclass(frozen=True, kw_only=True)
class ViomiSensorDescription(SensorEntityDescription):
    """Describes a Viomi sensor."""

    value_fn: Callable[[ViomiData], int | float | str | None]


def _hours(value: timedelta) -> int:
    return int(value.total_seconds() / 3600)


def _error(data: ViomiData) -> str | None:
    code = data.status.error_code
    if not code or code in ERRORS_FALSE_POSITIVE:
        return None
    return data.status.error


def _consumable(key: str, attribute: str) -> ViomiSensorDescription:
    """Hours the part has worked; the robot knows no lifetime and no replacement.

    The counter drops back to zero when it is reset (see the reset buttons).
    """
    return ViomiSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _hours(getattr(data.consumables, attribute)),
    )


SENSORS = (
    ViomiSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.status.battery,
    ),
    ViomiSensorDescription(
        key="cleaned_area",
        translation_key="cleaned_area",
        device_class=SensorDeviceClass.AREA,
        native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.status.clean_area,
    ),
    ViomiSensorDescription(
        key="cleaning_time",
        translation_key="cleaning_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: int(data.status.clean_time.total_seconds() / 60),
    ),
    ViomiSensorDescription(
        key="error",
        translation_key="error",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_error,
    ),
    _consumable("main_brush_hours", "main_brush"),
    _consumable("side_brush_hours", "side_brush"),
    _consumable("filter_hours", "filter"),
    _consumable("mop_hours", "mop"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ViomiConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Viomi sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(ViomiSensor(coordinator, desc) for desc in SENSORS)


class ViomiSensor(ViomiEntity, SensorEntity):
    """A sensor reading the coordinator data."""

    entity_description: ViomiSensorDescription

    def __init__(
        self, coordinator: ViomiCoordinator, description: ViomiSensorDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        # The battery sensor predates the others and keeps its unique id.
        self._attr_unique_id = f"{self._device_unique_id}_{description.key}"

    @property
    def native_value(self) -> int | float | str | None:
        """Return the value."""
        return self.entity_description.value_fn(self.coordinator.data)
