"""Switch platform for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AnkerSolixConfigEntry
from . import registers as regs
from .const import ACTIVE_CHARGING_STATUSES
from .coordinator import AnkerSolixCoordinator
from .entity import AnkerSolixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkerSolixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            AnkerSolixChargingSwitch(coordinator),
            AnkerSolixBoostSwitch(coordinator),
        ]
    )


class AnkerSolixChargingSwitch(AnkerSolixEntity, SwitchEntity):
    """Start and stop charging (holding register 21000).

    Register 21000 is a command, not a state: it holds 1 or 2 for the last
    command issued. The switch therefore reports the actual charging status
    from the telemetry block instead of reading the command back.
    """

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AnkerSolixCoordinator) -> None:
        super().__init__(coordinator, "charging")

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        status = self.coordinator.data.get("charging_status")
        if status is None:
            return None
        return int(status) in ACTIVE_CHARGING_STATUSES

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_start_charging()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_stop_charging()
        await self.coordinator.async_request_refresh()


class AnkerSolixBoostSwitch(AnkerSolixEntity, SwitchEntity):
    """Boost mode (holding register 21002).

    Per the protocol document this takes effect once per charging session, so
    turning it on does not necessarily stay on across sessions.
    """

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AnkerSolixCoordinator) -> None:
        super().__init__(coordinator, "boost_mode")

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        # Prefer the live telemetry reading; fall back to the written setting.
        raw = self.coordinator.data.get("boost_mode")
        if raw is None:
            raw = self.coordinator.data.get("boost_mode_setting")
        return None if raw is None else bool(raw)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_and_refresh(
            regs.CONTROL_BOOST_MODE.address, 1
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write_and_refresh(
            regs.CONTROL_BOOST_MODE.address, 0
        )
