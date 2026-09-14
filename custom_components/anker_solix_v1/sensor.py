"""Sensor platform for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AnkerSolixConfigEntry
from .const import (
    CHARGING_MODE,
    CHARGING_STATUS,
    CONNECTION_STATUS,
    CP_SIGNAL_STATUS,
    PHASE_MODE,
)
from .coordinator import AnkerSolixCoordinator
from .entity import AnkerSolixEntity
from .modbus import ChargerData

# Relay temperatures outside this band are treated as "no reading". The idle
# test device reports -55.0 C on relay 1, which is a sentinel rather than a
# measurement; a real enclosure sensor stays well inside these bounds.
TEMPERATURE_VALID_RANGE = (-40.0, 150.0)


@dataclass(frozen=True, kw_only=True)
class AnkerSensorDescription(SensorEntityDescription):
    """Describes one sensor, including how to pull its value from a poll."""

    value_fn: Callable[[ChargerData], Any] | None = None


def _enum_value(key: str, mapping: dict[int, str]) -> Callable[[ChargerData], Any]:
    """Build a value function mapping a raw register to a named state."""

    def _value(data: ChargerData) -> str | None:
        raw = data.get(key)
        if raw is None:
            return None
        return mapping.get(int(raw))

    return _value


def _plain(key: str) -> Callable[[ChargerData], Any]:
    """Build a value function returning a scaled register as-is."""
    return lambda data: data.get(key)


def _temperature(key: str) -> Callable[[ChargerData], Any]:
    """Build a value function that filters implausible temperature readings."""

    def _value(data: ChargerData) -> float | None:
        raw = data.get(key)
        if raw is None:
            return None
        low, high = TEMPERATURE_VALID_RANGE
        return raw if low <= raw <= high else None

    return _value


def _energy_kwh(key: str) -> Callable[[ChargerData], Any]:
    """Convert a Wh register to kWh for the energy dashboard."""

    def _value(data: ChargerData) -> float | None:
        raw = data.get(key)
        if raw is None:
            return None
        return round(raw / 1000, 3)

    return _value


SENSORS: tuple[AnkerSensorDescription, ...] = (
    AnkerSensorDescription(
        key="charging_status",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(CHARGING_STATUS.values())),
        value_fn=_enum_value("charging_status", CHARGING_STATUS),
    ),
    AnkerSensorDescription(
        key="cp_signal_status",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(CP_SIGNAL_STATUS.values())),
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_enum_value("cp_signal_status", CP_SIGNAL_STATUS),
    ),
    AnkerSensorDescription(
        key="phase_mode",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(PHASE_MODE.values())),
        value_fn=_enum_value("phase_mode", PHASE_MODE),
    ),
    AnkerSensorDescription(
        key="charging_mode",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(CHARGING_MODE.values())),
        value_fn=_enum_value("charging_mode", CHARGING_MODE),
    ),
    AnkerSensorDescription(
        key="ocpp_connection_status",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(CONNECTION_STATUS.values())),
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_enum_value("ocpp_connection_status", CONNECTION_STATUS),
    ),
    AnkerSensorDescription(
        key="mqtt_connection_status",
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(CONNECTION_STATUS.values())),
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_enum_value("mqtt_connection_status", CONNECTION_STATUS),
    ),
    # Power.
    AnkerSensorDescription(
        key="active_power_total",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=_plain("active_power_total"),
    ),
    *(
        AnkerSensorDescription(
            key=f"active_power_l{phase}",
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfPower.WATT,
            entity_registry_enabled_default=phase == 1,
            value_fn=_plain(f"active_power_l{phase}"),
        )
        for phase in (1, 2, 3)
    ),
    *(
        AnkerSensorDescription(
            key=f"reactive_power_l{phase}",
            device_class=SensorDeviceClass.REACTIVE_POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
            entity_registry_enabled_default=False,
            value_fn=_plain(f"reactive_power_l{phase}"),
        )
        for phase in (1, 2, 3)
    ),
    *(
        AnkerSensorDescription(
            key=f"apparent_power_l{phase}",
            device_class=SensorDeviceClass.APPARENT_POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
            entity_registry_enabled_default=False,
            value_fn=_plain(f"apparent_power_l{phase}"),
        )
        for phase in (1, 2, 3)
    ),
    # Voltage and current.
    *(
        AnkerSensorDescription(
            key=f"voltage_l{phase}_n",
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            entity_registry_enabled_default=phase == 1,
            value_fn=_plain(f"voltage_l{phase}_n"),
        )
        for phase in (1, 2, 3)
    ),
    *(
        AnkerSensorDescription(
            key=key,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            entity_registry_enabled_default=False,
            value_fn=_plain(key),
        )
        for key in ("voltage_l1_l2", "voltage_l2_l3", "voltage_l3_l1")
    ),
    *(
        AnkerSensorDescription(
            key=f"current_l{phase}",
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            entity_registry_enabled_default=phase == 1,
            value_fn=_plain(f"current_l{phase}"),
        )
        for phase in (1, 2, 3)
    ),
    # Session.
    AnkerSensorDescription(
        key="session_energy",
        device_class=SensorDeviceClass.ENERGY,
        # The charger resets this at the start of each session, so it is a
        # TOTAL rather than TOTAL_INCREASING: the latter would make Home
        # Assistant treat every reset as a meter rollover.
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=_energy_kwh("session_energy"),
    ),
    AnkerSensorDescription(
        key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        value_fn=_plain("session_duration"),
    ),
    # Diagnostics.
    *(
        AnkerSensorDescription(
            key=f"relay_{index}_temperature",
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=False,
            value_fn=_temperature(f"relay_{index}_temperature"),
        )
        for index in (1, 2)
    ),
    AnkerSensorDescription(
        key="cp_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_plain("cp_voltage"),
    ),
    AnkerSensorDescription(
        key="led_brightness",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_plain("led_brightness"),
    ),
    # Nameplate ratings, not measurements: they carry a unit for display but no
    # device_class, because a device_class would oblige a state_class and make
    # Home Assistant record statistics for a value that never changes.
    AnkerSensorDescription(
        key="rated_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_plain("rated_power"),
    ),
    AnkerSensorDescription(
        key="max_output_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_plain("max_output_current"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnkerSolixConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        AnkerSolixSensor(coordinator, description) for description in SENSORS
    )


class AnkerSolixSensor(AnkerSolixEntity, SensorEntity):
    """A single decoded register exposed as a sensor."""

    entity_description: AnkerSensorDescription

    def __init__(
        self,
        coordinator: AnkerSolixCoordinator,
        description: AnkerSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None or self.entity_description.value_fn is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
