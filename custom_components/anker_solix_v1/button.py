"""Button platform for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AnkerSolixConfigEntry
from .coordinator import AnkerSolixCoordinator
from .entity import AnkerSolixEntity
from .modbus import AnkerSolixModbusClient


@dataclass(frozen=True, kw_only=True)
class AnkerButtonDescription(ButtonEntityDescription):
    """Describes one command button."""

    press_fn: Callable[[AnkerSolixModbusClient], Awaitable[None]]


BUTTONS: tuple[AnkerButtonDescription, ...] = (
    AnkerButtonDescription(
        key="start_charging",
        press_fn=lambda client: client.async_start_charging(),
    ),
    AnkerButtonDescription(
        key="stop_charging",
        press_fn=lambda client: client.async_stop_charging(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkerSolixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the command buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        AnkerSolixButton(coordinator, description) for description in BUTTONS
    )


class AnkerSolixButton(AnkerSolixEntity, ButtonEntity):
    """A one-shot charging command.

    The switch covers the usual start/stop case; these buttons exist because a
    command register accepts a repeated command, which a switch already in the
    desired state will not send.
    """

    entity_description: AnkerButtonDescription

    def __init__(
        self,
        coordinator: AnkerSolixCoordinator,
        description: AnkerButtonDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator.client)
        await self.coordinator.async_request_refresh()
