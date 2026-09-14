"""Modbus TCP client for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from pymodbus.client import AsyncModbusTcpClient

from . import registers as regs
from .const import (
    CHARGING_COMMAND_START,
    CHARGING_COMMAND_STOP,
    MODEL_FALLBACK,
)

_LOGGER = logging.getLogger(__name__)


class AnkerSolixError(Exception):
    """Raised when the charger cannot be read or written."""


@dataclass
class ChargerData:
    """One poll's worth of decoded values."""

    values: dict[str, Any] = field(default_factory=dict)
    strings: dict[str, str] = field(default_factory=dict)
    control: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Look a value up across telemetry and control registers."""
        if key in self.values:
            return self.values[key]
        return self.control.get(key, default)


class AnkerSolixModbusClient:
    """Talks Modbus TCP to the charger over one persistent connection.

    The charger accepts at most two simultaneous clients, so the connection is
    opened once and reused; reconnecting per poll would burn through the client
    slots and lock out other consumers such as an EMS.
    """

    def __init__(self, host: str, port: int, device_id: int) -> None:
        self._host = host
        self._port = port
        self._device_id = device_id
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    async def _ensure_connected(self) -> AsyncModbusTcpClient:
        """Return a connected client, reconnecting if the link dropped."""
        if self._client is not None and self._client.connected:
            return self._client

        client = self._client or AsyncModbusTcpClient(self._host, port=self._port)
        self._client = client
        await client.connect()
        if not client.connected:
            raise AnkerSolixError(f"Cannot connect to {self._host}:{self._port}")
        return client

    async def close(self) -> None:
        """Drop the connection and free the charger's client slot."""
        async with self._lock:
            if self._client is not None:
                self._client.close()
                self._client = None

    async def async_read(self) -> ChargerData:
        """Read telemetry and control registers in two block reads."""
        async with self._lock:
            client = await self._ensure_connected()

            # Telemetry lives in input registers (FC4); the holding block (FC3)
            # carries configuration. Each block is fetched in a single request.
            telemetry = await self._read(
                client,
                client.read_input_registers,
                regs.INPUT_BLOCK_START,
                regs.INPUT_BLOCK_COUNT,
            )
            control = await self._read(
                client,
                client.read_holding_registers,
                regs.HOLDING_BLOCK_START,
                regs.HOLDING_BLOCK_COUNT,
            )

        data = ChargerData()

        for register in regs.INPUT_REGISTERS:
            data.values[register.name] = regs.decode(register, telemetry)

        for register in regs.STRINGS:
            value = regs.decode_string(register, telemetry)
            if value is not None:
                data.strings[register.name] = value

        for register in regs.HOLDING_REGISTERS:
            offset = register.address - regs.HOLDING_BLOCK_START
            if offset < 0 or offset + register.words > len(control):
                continue
            raw = control[offset]
            data.control[register.name] = (
                raw if register.gain == 1 else raw / register.gain
            )

        return data

    async def _read(
        self,
        client: AsyncModbusTcpClient,
        reader: Any,
        address: int,
        count: int,
    ) -> list[int]:
        """Perform one block read, translating failures into AnkerSolixError."""
        try:
            result = await reader(address, count=count, device_id=self._device_id)
        except Exception as err:  # pymodbus raises a broad set of exceptions
            self._invalidate()
            raise AnkerSolixError(f"Read of {address} failed: {err}") from err

        if result.isError():
            raise AnkerSolixError(f"Charger rejected read of {address}: {result}")

        return list(result.registers)

    def _invalidate(self) -> None:
        """Force a reconnect on the next call after a transport failure."""
        if self._client is not None:
            self._client.close()
            self._client = None

    async def async_write_register(self, address: int, value: int) -> None:
        """Write one holding register."""
        async with self._lock:
            client = await self._ensure_connected()
            try:
                result = await client.write_register(
                    address, value, device_id=self._device_id
                )
            except Exception as err:
                self._invalidate()
                raise AnkerSolixError(f"Write to {address} failed: {err}") from err

        if result.isError():
            raise AnkerSolixError(f"Charger rejected write to {address}: {result}")

        _LOGGER.debug("Wrote %s to register %s", value, address)

    async def async_set_max_current(self, amperes: float) -> None:
        """Set the charging current limit, in amperes."""
        await self.async_write_register(
            regs.CONTROL_MAX_CURRENT.address,
            round(amperes * regs.CONTROL_MAX_CURRENT.gain),
        )

    async def async_start_charging(self) -> None:
        """Issue the start command."""
        await self.async_write_register(
            regs.CONTROL_CHARGING_COMMAND.address, CHARGING_COMMAND_START
        )

    async def async_stop_charging(self) -> None:
        """Issue the stop command."""
        await self.async_write_register(
            regs.CONTROL_CHARGING_COMMAND.address, CHARGING_COMMAND_STOP
        )

    async def async_probe(self) -> dict[str, str]:
        """Verify the charger answers and return its identity.

        Used by the config flow, so it reads only what identifies the device.
        """
        async with self._lock:
            client = await self._ensure_connected()
            telemetry = await self._read(
                client,
                client.read_input_registers,
                regs.INPUT_BLOCK_START,
                regs.INPUT_BLOCK_COUNT,
            )

        identity: dict[str, str] = {}
        for register in regs.STRINGS:
            value = regs.decode_string(register, telemetry)
            if value is not None:
                identity[register.name] = value

        if "serial_number" not in identity:
            raise AnkerSolixError("Device did not report a serial number")

        identity.setdefault("model_name", MODEL_FALLBACK)
        return identity
