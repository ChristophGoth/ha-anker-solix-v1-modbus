"""Shared entity base for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AnkerSolixCoordinator


class AnkerSolixEntity(CoordinatorEntity[AnkerSolixCoordinator]):
    """Base entity wiring every platform to the shared coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AnkerSolixCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key

    @property
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info
