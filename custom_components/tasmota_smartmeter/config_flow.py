"""Config flow for Tasmota Smart Meter."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import MeterAuthError, MeterError, TasmotaMeterApi
from .const import DOMAIN

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_HOST): str, vol.Optional(CONF_PASSWORD): PASSWORD}
)


async def _validate(hass, data: Mapping[str, Any]) -> tuple[dict | None, str | None]:
    api = TasmotaMeterApi(async_get_clientsession(hass), data[CONF_HOST], data.get(CONF_PASSWORD))
    try:
        status = await api.status()
        rows = await api.rows()
    except MeterAuthError:
        return None, "invalid_auth"
    except MeterError:
        return None, "cannot_connect"
    if not rows:
        return None, "no_meter_data"
    return status, None


class TasmotaMeterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasmota Smart Meter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            status, error = await _validate(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(format_mac(status["mac"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})
                return self.async_create_entry(title=status["name"], data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input.get(CONF_PASSWORD)}
            status, error = await _validate(self.hass, data)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(format_mac(status["mac"]))
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input.get(CONF_PASSWORD)}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Optional(CONF_PASSWORD): PASSWORD}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            status, error = await _validate(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(format_mac(status["mac"]))
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input or entry.data),
            errors=errors,
        )
