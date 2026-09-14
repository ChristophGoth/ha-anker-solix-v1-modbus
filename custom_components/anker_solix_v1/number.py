"""Number platform for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AnkerSolixConfigEntry
from . import registers as regs
from .const import (
    MAX_CHARGING_CURRENT,
    MAX_TIMEOUT,
    MIN_CHARGING_CURRENT,
    MIN_TIMEOUT,
)
from .coordinator import AnkerSolixCoordinator
from .entity import AnkerSolixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkerSolixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the writable numbers."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            AnkerSolixMaxCurrentNumber(coordinator),
            AnkerSolixTimeoutNumber(coordinator),
        ]
    )


class AnkerSolixMaxCurrentNumber(AnkerSolixEntity, NumberEntity):
    """The charging current limit (holding register 21001)."""

    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_mode = NumberMode.SLIDER
    # The charger pauses below 6 A, so the slider does not offer lower values.
    _attr_native_min_value = float(MIN_CHARGING_CURRENT)
    _attr_native_step = 1.0

    def __init__(self, coordinator: AnkerSolixCoordinator) -> None:
        super().__init__(coordinator, "max_current_setting")

    @property
    def native_max_value(self) -> float:
        """Use the charger's own rating when it reports one."""
        if self.coordinator.data is not None:
            rated = self.coordinator.data.get("max_output_current")
            if rated:
                return float(rated)
        return float(MAX_CHARGING_CURRENT)

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("max_current_setting")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_max_current(value)
        await self.coordinator.async_request_refresh()


class AnkerSolixTimeoutNumber(AnkerSolixEntity, NumberEntity):
    """The Modbus control timeout (holding register 21003).

    The charger falls back to its own strategy if control traffic stops for
    longer than this, so it must stay comfortably above the poll interval.
    """

    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = float(MIN_TIMEOUT)
    _attr_native_max_value = float(MAX_TIMEOUT)
    _attr_native_step = 1.0
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AnkerSolixCoordinator) -> None:
        super().__init__(coordinator, "timeout_setting")

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("timeout_setting")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write_and_refresh(
            regs.CONTROL_TIMEOUT.address, int(value)
        )
