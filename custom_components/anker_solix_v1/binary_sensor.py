"""Binary sensor platform for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AnkerSolixConfigEntry
from . import registers as regs
from .const import ACTIVE_CHARGING_STATUSES
from .coordinator import AnkerSolixCoordinator
from .entity import AnkerSolixEntity
from .modbus import ChargerData

# CP states where a vehicle is physically connected (B, C and D families).
VEHICLE_CONNECTED_CP_STATES = {3, 4, 5, 6, 8, 9}


def _flag(key: str) -> Callable[[ChargerData], bool | None]:
    """Build a value function for a 0/1 register."""

    def _value(data: ChargerData) -> bool | None:
        raw = data.get(key)
        return None if raw is None else bool(raw)

    return _value


def _charging(data: ChargerData) -> bool | None:
    raw = data.get("charging_status")
    return None if raw is None else int(raw) in ACTIVE_CHARGING_STATUSES


def _vehicle_connected(data: ChargerData) -> bool | None:
    raw = data.get("cp_signal_status")
    return None if raw is None else int(raw) in VEHICLE_CONNECTED_CP_STATES


def _any_alarm(data: ChargerData) -> bool | None:
    """Aggregate the twelve alarm bitfields into one flag.

    The per-bit alarm list ships in a separate document that is not available,
    so individual causes are not decoded; the raw words are exposed as
    attributes for anyone who does have the list.
    """
    values = [data.get(register.name) for register in regs.ALARM_REGISTERS]
    if all(value is None for value in values):
        return None
    return any(bool(value) for value in values if value is not None)


@dataclass(frozen=True, kw_only=True)
class AnkerBinarySensorDescription(BinarySensorEntityDescription):
    """Describes one binary sensor."""

    value_fn: Callable[[ChargerData], bool | None]


BINARY_SENSORS: tuple[AnkerBinarySensorDescription, ...] = (
    AnkerBinarySensorDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=_charging,
    ),
    AnkerBinarySensorDescription(
        key="vehicle_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=_vehicle_connected,
    ),
    AnkerBinarySensorDescription(
        key="alarm_active",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_any_alarm,
    ),
    AnkerBinarySensorDescription(
        key="pwm_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_flag("pwm_enabled"),
    ),
    AnkerBinarySensorDescription(
        key="load_balancing_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_flag("load_balancing_enabled"),
    ),
    AnkerBinarySensorDescription(
        key="solar_balancing_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_flag("solar_balancing_enabled"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkerSolixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        AnkerSolixBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class AnkerSolixBinarySensor(AnkerSolixEntity, BinarySensorEntity):
    """A derived on/off state of the charger."""

    entity_description: AnkerBinarySensorDescription

    def __init__(
        self,
        coordinator: AnkerSolixCoordinator,
        description: AnkerBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Expose the raw alarm words so a bit list can be applied later."""
        if self.entity_description.key != "alarm_active":
            return None
        if self.coordinator.data is None:
            return None
        return {
            register.name: value
            for register in regs.ALARM_REGISTERS
            if (value := self.coordinator.data.get(register.name)) is not None
        }
