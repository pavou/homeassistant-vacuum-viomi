"""Base entity for Xiaomi Viomi."""

from homeassistant.const import CONF_MAC, CONF_MODEL
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ViomiCoordinator


class ViomiEntity(CoordinatorEntity[ViomiCoordinator]):
    """Base class of the Viomi entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ViomiCoordinator) -> None:
        """Initialize the entity and its device."""
        super().__init__(coordinator)
        entry = coordinator.config_entry

        # The config entry's unique id is the device MAC; entity unique ids are
        # derived from it so that they stay stable across releases.
        self._device_unique_id = entry.unique_id or entry.entry_id

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_unique_id)},
            manufacturer="Xiaomi",
            model=entry.data.get(CONF_MODEL),
            name=entry.title,
        )
        if mac := entry.data.get(CONF_MAC):
            device_info["connections"] = {(CONNECTION_NETWORK_MAC, mac)}
        self._attr_device_info = device_info
