"""Update coordinator for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, MANUFACTURER, MODEL_FALLBACK
from .modbus import AnkerSolixError, AnkerSolixModbusClient, ChargerData

_LOGGER = logging.getLogger(__name__)


class AnkerSolixCoordinator(DataUpdateCoordinator[ChargerData]):
    """Polls the charger and shares one snapshot with every entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: AnkerSolixModbusClient,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.entry = entry
        self.serial_number: str | None = None
        self._model: str = MODEL_FALLBACK
        self._software_version: str | None = None
        self._hardware_version: str | None = None

    async def _async_update_data(self) -> ChargerData:
        try:
            data = await self.client.async_read()
        except AnkerSolixError as err:
            raise UpdateFailed(str(err)) from err

        # Device identity is static, but it arrives in the same block read, so
        # it is cached here rather than costing a separate request.
        self.serial_number = data.strings.get("serial_number", self.serial_number)
        self._model = data.strings.get("model_name", self._model)
        self._software_version = data.strings.get(
            "software_version", self._software_version
        )
        self._hardware_version = data.strings.get(
            "hardware_version", self._hardware_version
        )
        return data

    @property
    def device_info(self) -> DeviceInfo:
        """Device registry entry shared by every entity of this charger."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            manufacturer=MANUFACTURER,
            model=self._model,
            name=self.entry.title,
            serial_number=self.serial_number,
            sw_version=self._software_version,
            hw_version=self._hardware_version,
        )

    async def async_write_and_refresh(self, address: int, value: int) -> None:
        """Write a register, then refresh so entities reflect the new state."""
        await self.client.async_write_register(address, value)
        await self.async_request_refresh()
