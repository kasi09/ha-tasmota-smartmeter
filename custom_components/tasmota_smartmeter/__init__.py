"""Tasmota Smart Meter: all values of a Tasmota IR reader, read over HTTP.

Reads the sensor table of the Tasmota web page, which shows every value the
meter script decodes - the JSON endpoint often carries only part of them.
Nothing on the device is changed; no MQTT is needed.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeterAuthError, MeterError, TasmotaMeterApi
from .const import DOMAIN
from .coordinator import MeterCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type MeterConfigEntry = ConfigEntry[MeterCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MeterConfigEntry) -> bool:
    api = TasmotaMeterApi(
        async_get_clientsession(hass), entry.data[CONF_HOST], entry.data.get(CONF_PASSWORD)
    )
    try:
        status = await api.status()
    except MeterAuthError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="invalid_auth"
        ) from err
    except MeterError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN, translation_key="cannot_connect"
        ) from err
    coordinator = MeterCoordinator(hass, entry, api, status)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeterConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
