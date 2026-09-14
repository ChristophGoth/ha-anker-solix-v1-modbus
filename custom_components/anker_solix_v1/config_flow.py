"""Config flow for the Anker SOLIX V1 Smart EV Charger."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import callback

from .const import (
    CONF_DEVICE_ID,
    DEFAULT_DEVICE_ID,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .modbus import AnkerSolixError, AnkerSolixModbusClient

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Optional(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): vol.Coerce(int),
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): vol.All(vol.Coerce(int), vol.Range(min=2, max=300)),
    }
)


class AnkerSolixConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI configuration flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for connection details and verify the charger answers."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = AnkerSolixModbusClient(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                device_id=user_input[CONF_DEVICE_ID],
            )
            try:
                identity = await client.async_probe()
            except AnkerSolixError:
                errors["base"] = "cannot_connect"
            else:
                serial = identity["serial_number"]
                await self.async_set_unique_id(serial)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=identity.get("model_name") or serial,
                    data=user_input,
                )
            finally:
                await client.close()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return AnkerSolixOptionsFlow()


class AnkerSolixOptionsFlow(OptionsFlow):
    """Allow the poll interval to be changed after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=2, max=300)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
