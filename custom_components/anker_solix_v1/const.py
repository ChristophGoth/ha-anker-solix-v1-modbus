"""Constants for the Anker SOLIX V1 Smart EV Charger integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "anker_solix_v1"

CONF_DEVICE_ID: Final = "device_id"

DEFAULT_PORT: Final = 502
DEFAULT_DEVICE_ID: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 5

MANUFACTURER: Final = "Anker"
MODEL_FALLBACK: Final = "SOLIX V1 Smart EV Charger"

# The charger accepts at most two simultaneous Modbus clients (e.g. an EMS and a
# debugging tool), so the client keeps a single persistent connection instead of
# reconnecting on every poll.
MAX_CONCURRENT_CLIENTS: Final = 2

# Charging Status (input register 20097).
CHARGING_STATUS: Final[dict[int, str]] = {
    0: "idle",
    1: "preparing",
    2: "charging",
    3: "charger_paused",
    4: "vehicle_paused",
    5: "charging_completed",
    6: "reserving",
    7: "disabled",
    8: "error",
}

# CP Signal Status (input register 20092). The IEC 61851 control pilot state.
CP_SIGNAL_STATUS: Final[dict[int, str]] = {
    0: "a_12v",
    3: "b1_9v",
    4: "b2_9v",
    5: "c1_6v",
    6: "c2_6v",
    7: "error",
    8: "d1_3v",
    9: "d2_3v",
    10: "e_0v",
    11: "f_minus_12v",
}

# Single / Three-Phase Operating Mode (input register 20087).
PHASE_MODE: Final[dict[int, str]] = {
    1: "single_phase",
    3: "three_phase",
}

# Charging Mode (input register 20088).
CHARGING_MODE: Final[dict[int, str]] = {
    0: "solar_and_grid",
    1: "only_solar",
}

# Connection status shared by OCPP (20099) and MQTT (20100). The documentation
# lists "2: Connected" for OCPP but only "1: Connected" for MQTT; both values are
# mapped so either firmware reading resolves to a name.
CONNECTION_STATUS: Final[dict[int, str]] = {
    0: "not_connected",
    1: "connecting",
    2: "connected",
}

# Set the Number of Charging Phases (holding register 21005).
PHASE_SETTING: Final[dict[int, str]] = {
    0: "automatic",
    1: "fixed_single_phase",
    2: "fixed_three_phase",
}
PHASE_SETTING_REVERSE: Final[dict[str, int]] = {
    value: key for key, value in PHASE_SETTING.items()
}

# Charging Command (holding register 21000).
CHARGING_COMMAND_START: Final = 1
CHARGING_COMMAND_STOP: Final = 2

# The charger pauses below 6 A, so the number entity does not offer lower values.
MIN_CHARGING_CURRENT: Final = 6
# Absolute ceiling; the actual limit is read from register 20039 per device.
MAX_CHARGING_CURRENT: Final = 32

# Timeout bounds (holding register 21003). The documentation requires > 5 s.
MIN_TIMEOUT: Final = 6
MAX_TIMEOUT: Final = 3600

# Statuses in which the charger is actively delivering energy.
ACTIVE_CHARGING_STATUSES: Final = {2}
