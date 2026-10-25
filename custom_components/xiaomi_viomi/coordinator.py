"""Data update coordinator for Xiaomi Viomi."""

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from miio import DeviceException
from miio.integrations.vacuum.roborock.vacuumcontainers import DNDStatus
from miio.integrations.vacuum.viomi.viomivacuum import (
    ViomiConsumableStatus,
    ViomiVacuum,
    ViomiVacuumStatus,
)

from .const import DEVICE_PROPERTIES, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type ViomiConfigEntry = ConfigEntry[ViomiCoordinator]


class PatchedViomiVacuum(ViomiVacuum):
    """Viomi vacuum with the commands python-miio does not provide."""

    def locate(self) -> None:
        """Locate a device."""
        self.send("set_resetpos", [1])


@dataclass(frozen=True)
class ViomiData:
    """Snapshot of the device state."""

    status: ViomiVacuumStatus
    consumables: ViomiConsumableStatus
    dnd: DNDStatus


class ViomiCoordinator(DataUpdateCoordinator[ViomiData]):
    """Poll a Viomi vacuum."""

    config_entry: ViomiConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ViomiConfigEntry,
        device: PatchedViomiVacuum,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device

    def _fetch(self) -> ViomiData:
        # Override of miio's ViomiVacuum.status() because of a bug in it.
        properties = {}
        for prop in DEVICE_PROPERTIES:
            value = self.device.send("get_prop", [prop])
            properties[prop] = value[0] if len(value) else None

        return ViomiData(
            status=ViomiVacuumStatus(properties),
            consumables=self.device.consumable_status(),
            dnd=self.device.dnd_status(),
        )

    async def _async_update_data(self) -> ViomiData:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except (OSError, DeviceException) as exc:
            raise UpdateFailed(f"Error fetching the vacuum state: {exc}") from exc
