"""Register map for the Anker SOLIX V1 Smart EV Charger.

Derived from "Anker SOLIX V1 Smart EV Charger Modbus Protocol" V1.0.0
(30-11-2025), and verified against an A5191 (SW 1.0.6.1) over Modbus TCP.

Two findings from that verification are not in the document and matter here:

* The 20000 block answers only to function code 4 (input registers); the 21000
  block answers only to function code 3/6 (holding registers). The document
  distinguishes registers by RO/RW but never names a function code.
* 32-bit values are big-endian word order, confirmed via Rated Power, which
  reads [0, 7400] -> 7400 W (little-endian would give 484966400 W).

Where the document's unit column contradicts the observed value, the observed
value wins and the discrepancy is noted on the entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Input register block (function code 4), read-only telemetry.
INPUT_BLOCK_START = 20000
INPUT_BLOCK_COUNT = 101  # 20000..20100 inclusive

# Holding register block (function code 3/6), configuration and control.
HOLDING_BLOCK_START = 21000
HOLDING_BLOCK_COUNT = 6  # 21000..21005 inclusive


@dataclass(frozen=True)
class Register:
    """One logical value in the register map.

    `gain` is the divisor applied to the raw reading, matching the document's
    Gain column: a gain of 10 on a voltage register means the raw value is in
    tenths of a volt.
    """

    address: int
    name: str
    words: int = 1
    gain: int = 1
    signed: bool = False
    unit: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class StringRegister:
    """An ASCII string spanning several registers, NUL-padded."""

    address: int
    name: str
    words: int


# --- Intrinsic information -------------------------------------------------

STRINGS: tuple[StringRegister, ...] = (
    StringRegister(20001, "model_name", 10),
    StringRegister(20011, "serial_number", 12),
    StringRegister(20023, "software_version", 6),
    StringRegister(20029, "hardware_version", 6),
)

DEVICE_INFO: tuple[Register, ...] = (
    Register(20000, "product_number"),
    # The document lists these three as INT32 at 20035/20037/20039 with units
    # W/W/KVA. On the test device 20035+20036 reads [0, 7400] (7400 W rated) and
    # 20039+20040 reads [0, 32] (32 A max), so the third is a current in amperes,
    # not apparent power. All three are signed per the document; in practice the
    # sign never engages, since bit 31 would mean values above 2.1 billion.
    Register(20035, "rated_power", words=2, signed=True, unit="W"),
    # Reads 0 on the A5191 rather than the 6 A the document calls the system
    # minimum, so it is not surfaced as an entity; MIN_CHARGING_CURRENT in
    # const.py carries that limit instead.
    Register(20037, "min_output_current", words=2, signed=True, unit="A"),
    Register(
        20039,
        "max_output_current",
        words=2,
        signed=True,
        unit="A",
        note="Document says KVA; observed value is the 32 A current rating.",
    ),
)

# --- Alarms ----------------------------------------------------------------

# Twelve bitfields, one bit per alarm. The alarm list itself is in a separate
# document that is not available, so the bits are surfaced as raw words plus an
# aggregate "any alarm active" flag rather than being decoded individually.
ALARM_REGISTERS: tuple[Register, ...] = tuple(
    Register(address, f"alarm_information_{index}")
    for index, address in enumerate(range(20041, 20053), start=1)
)

# --- AC charging information ----------------------------------------------

VOLTAGE_REGISTERS: tuple[Register, ...] = (
    Register(20053, "voltage_l1_n", gain=10, unit="V"),
    Register(20054, "voltage_l2_n", gain=10, unit="V"),
    Register(20055, "voltage_l3_n", gain=10, unit="V"),
    Register(20056, "voltage_l1_l2", gain=10, unit="V"),
    Register(20057, "voltage_l2_l3", gain=10, unit="V"),
    Register(20058, "voltage_l3_l1", gain=10, unit="V"),
)

# The document gives gain 100 for these, but the observed value contradicts it:
# while charging at 1388 W on L1 at 224.0 V, register 20059 reads 62. Gain 10
# yields 6.2 A (6.2 x 224.0 = 1388.8 W, within 0.1 % of the reported power);
# gain 100 would give 0.62 A and 138.9 W, off by a factor of ten. L2/L3 share
# the block and the document entry, and are corrected with it.
CURRENT_REGISTERS: tuple[Register, ...] = (
    Register(20059, "current_l1", gain=10, unit="A", note="documented gain 100 reads 10x low; verified against active power"),
    Register(20060, "current_l2", gain=10, unit="A", note="documented gain 100 reads 10x low; verified against active power"),
    Register(20061, "current_l3", gain=10, unit="A", note="documented gain 100 reads 10x low; verified against active power"),
)

POWER_REGISTERS: tuple[Register, ...] = (
    Register(20062, "active_power_l1", words=2, unit="W"),
    Register(20064, "active_power_l2", words=2, unit="W"),
    Register(20066, "active_power_l3", words=2, unit="W"),
    Register(20068, "active_power_total", words=2, unit="W"),
    Register(20070, "reactive_power_l1", words=2, unit="var"),
    Register(20072, "reactive_power_l2", words=2, unit="var"),
    Register(20074, "reactive_power_l3", words=2, unit="var"),
    Register(20076, "apparent_power_l1", words=2, unit="VA"),
    Register(20078, "apparent_power_l2", words=2, unit="VA"),
    Register(20080, "apparent_power_l3", words=2, unit="VA"),
)

SESSION_REGISTERS: tuple[Register, ...] = (
    Register(20082, "session_duration", words=2, unit="s"),
    Register(20084, "session_energy", words=2, unit="Wh"),
)

STATUS_REGISTERS: tuple[Register, ...] = (
    Register(20086, "pwm_enabled"),
    Register(20087, "phase_mode"),
    Register(20088, "charging_mode"),
    Register(20089, "load_balancing_enabled"),
    Register(20090, "solar_balancing_enabled"),
    # Millivolts, confirmed across three CP states in one session: 11779 at A,
    # 8846 at B1 and 5826 at C2 land within 0.25 V of the IEC 61851 nominals
    # (12/9/6 V), all three low by a consistent ~0.2 V. No other gain fits —
    # gain 1 would put CP state A at 11.8 kV.
    Register(
        20091,
        "cp_voltage",
        gain=1000,
        unit="V",
        note="Document gives no unit; verified as millivolts against IEC 61851.",
    ),
    Register(20092, "cp_signal_status"),
    # The document gives gain 1 for both temperatures; gain 10 is correct.
    # Confirmed during a live charge (~1430 W on L1, twelve samples over two
    # minutes): relay 2 read 251..253, i.e. 25.1..25.3 C, drifting upward with
    # load as a real sensor does. Gain 1 would mean 251 C on a warm enclosure.
    #
    # Relay 1 held -550 across that same charge, unchanged to the digit. It is
    # an invalid-reading sentinel (-55.0 C), not a measurement: this unit has no
    # populated sensor on that channel. The sensor platform filters it out, so
    # the entity stays unavailable rather than charting a constant -55 C.
    Register(
        20093,
        "relay_1_temperature",
        gain=10,
        signed=True,
        unit="°C",
        note="Document says gain 1; verified as 10 during a live charge.",
    ),
    Register(
        20094,
        "relay_2_temperature",
        gain=10,
        signed=True,
        unit="°C",
        note="Document says gain 1; verified as 10 during a live charge.",
    ),
    Register(20095, "boost_mode"),
    Register(20096, "led_brightness", unit="%"),
    Register(20097, "charging_status"),
    Register(20099, "ocpp_connection_status"),
    Register(20100, "mqtt_connection_status"),
)

# --- AC control information (holding registers) ---------------------------

CONTROL_CHARGING_COMMAND = Register(21000, "charging_command")
# Document's unit column says W; the observed 320 matches the 32 A configured in
# the Anker app, so this is deci-amperes.
CONTROL_MAX_CURRENT = Register(
    21001,
    "max_current_setting",
    gain=10,
    unit="A",
    note="Document says W; verified as 0.1 A steps against the app.",
)
CONTROL_BOOST_MODE = Register(21002, "boost_mode_setting")
CONTROL_TIMEOUT = Register(
    21003,
    "timeout_setting",
    unit="s",
    note="Document's unit column says A; the value is seconds.",
)
CONTROL_PHASES = Register(21005, "phase_setting")

HOLDING_REGISTERS: tuple[Register, ...] = (
    CONTROL_CHARGING_COMMAND,
    CONTROL_MAX_CURRENT,
    CONTROL_BOOST_MODE,
    CONTROL_TIMEOUT,
    CONTROL_PHASES,
)

# Every input register that the coordinator decodes from one block read.
INPUT_REGISTERS: tuple[Register, ...] = (
    DEVICE_INFO
    + ALARM_REGISTERS
    + VOLTAGE_REGISTERS
    + CURRENT_REGISTERS
    + POWER_REGISTERS
    + SESSION_REGISTERS
    + STATUS_REGISTERS
)


def decode(register: Register, words: list[int]) -> float | int | None:
    """Turn raw register words into a scaled value.

    `words` holds the whole block; the register's own words are sliced out by
    address. Returns None when the block does not cover the register.
    """
    offset = register.address - INPUT_BLOCK_START
    if offset < 0 or offset + register.words > len(words):
        return None

    raw = 0
    for word in words[offset : offset + register.words]:
        raw = (raw << 16) | word

    if register.signed:
        bits = 16 * register.words
        if raw >= 1 << (bits - 1):
            raw -= 1 << bits

    if register.gain == 1:
        return raw
    return raw / register.gain


def decode_string(register: StringRegister, words: list[int]) -> str | None:
    """Decode a NUL-padded ASCII string from a block read."""
    offset = register.address - INPUT_BLOCK_START
    if offset < 0 or offset + register.words > len(words):
        return None

    raw = bytearray()
    for word in words[offset : offset + register.words]:
        raw.append((word >> 8) & 0xFF)
        raw.append(word & 0xFF)

    text = raw.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
    return text or None
