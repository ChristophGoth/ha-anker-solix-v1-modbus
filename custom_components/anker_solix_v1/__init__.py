"""The Anker SOLIX V1 Smart EV Charger integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_DEVICE_ID,
    DEFAULT_DEVICE_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import AnkerSolixCoordinator
from .modbus import AnkerSolixModbusClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type AnkerSolixConfigEntry = ConfigEntry[AnkerSolixCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AnkerSolixConfigEntry) -> bool:
    """Set up the charger from a config entry."""
    client = AnkerSolixModbusClient(
        host=entry.data[CONF_HOST],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        device_id=entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
    )

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    coordinator = AnkerSolixCoordinator(hass, entry, client, scan_interval)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.close()
        raise

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AnkerSolixConfigEntry) -> bool:
    """Unload a config entry and release the charger's client slot."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: AnkerSolixConfigEntry) -> None:
    """Reload when the options (e.g. scan interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)
