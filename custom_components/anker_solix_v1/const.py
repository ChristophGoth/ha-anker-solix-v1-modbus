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

# OCPP connection status (input register 20099): three states, where 1 is the
# transient one.
OCPP_CONNECTION_STATUS: Final[dict[int, str]] = {
    0: "not_connected",
    1: "connecting",
    2: "connected",
}

# MQTT connection status (input register 20100). The documentation gives this
# register only two states, and 1 means Connected here — not "connecting" as it
# does for OCPP above. The two registers previously shared one mapping, which
# reported a live MQTT link (the Anker cloud transport, normally 1) as
# "Connecting" forever.
MQTT_CONNECTION_STATUS: Final[dict[int, str]] = {
    0: "not_connected",
    1: "connected",
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

# Plain-text charging state for third-party consumers that read Home Assistant
# over the REST API. An ENUM sensor always serves its raw option there —
# translations are applied by the frontend only — so a tool like Leapmotor Mate
# would display "charger_paused" verbatim. This collapses the nine charger
# states onto the four words such tools expect, in English, as a display string.
CHARGING_STATE_TEXT: Final[dict[int, str]] = {
    0: "Idle",
    1: "Connected",
    2: "Charging",
    3: "Connected",
    4: "Connected",
    5: "Connected",
    6: "Connected",
    7: "Idle",
    8: "Error",
}
