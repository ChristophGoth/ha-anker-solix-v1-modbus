"""Select platform for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AnkerSolixConfigEntry
from . import registers as regs
from .const import PHASE_SETTING, PHASE_SETTING_REVERSE
from .coordinator import AnkerSolixCoordinator
from .entity import AnkerSolixEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkerSolixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the selects."""
    async_add_entities([AnkerSolixPhaseSelect(entry.runtime_data)])


class AnkerSolixPhaseSelect(AnkerSolixEntity, SelectEntity):
    """Phase mode (holding register 21005).

    On a single-phase charger the fixed three-phase option has no effect; the
    charger keeps reporting single-phase operation on register 20087.
    """

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(PHASE_SETTING.values())

    def __init__(self, coordinator: AnkerSolixCoordinator) -> None:
        super().__init__(coordinator, "phase_setting")

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get("phase_setting")
        if raw is None:
            return None
        return PHASE_SETTING.get(int(raw))

    async def async_select_option(self, option: str) -> None:
        value = PHASE_SETTING_REVERSE.get(option)
        if value is None:
            return
        await self.coordinator.async_write_and_refresh(
            regs.CONTROL_PHASES.address, value
        )
