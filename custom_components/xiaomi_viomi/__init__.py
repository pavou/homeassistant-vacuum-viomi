"""Xiaomi Viomi integration."""

from homeassistant.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_NAME,
    CONF_TOKEN,
    Platform,
)
from homeassistant.core import HomeAssistant

from .coordinator import PatchedViomiVacuum, ViomiConfigEntry, ViomiCoordinator

PLATFORMS = [Platform.VACUUM, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ViomiConfigEntry) -> bool:
    """Set up Xiaomi Viomi from a config entry."""
    if CONF_MODEL not in entry.data:
        # Entries created by 0.0.3 do not have the name and the model stored.
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_NAME: entry.title, CONF_MODEL: entry.title},
        )

    device = PatchedViomiVacuum(entry.data[CONF_HOST], entry.data[CONF_TOKEN])
    coordinator = ViomiCoordinator(hass, entry, device)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ViomiConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
