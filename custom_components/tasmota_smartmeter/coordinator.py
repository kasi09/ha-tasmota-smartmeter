"""Polls the reader and applies the plausibility guard to meter readings."""

from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeterAuthError, MeterError, TasmotaMeterApi
from .const import SCAN_INTERVAL
from .guard import MeterGuard
from .parser import Row

_LOGGER = logging.getLogger(__name__)


class MeterCoordinator(DataUpdateCoordinator[dict[str, Row]]):
    """Latest rows by key. Meter readings pass the guard first."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: TasmotaMeterApi,
        status: dict[str, Any],
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name="meter", update_interval=SCAN_INTERVAL
        )
        self.api = api
        self.status = status
        self.guarded: set[str] = set()      # keys of total_increasing sensors
        self.guards: dict[str, MeterGuard] = {}

    async def _async_update_data(self) -> dict[str, Row]:
        try:
            rows = await self.api.rows()
        except MeterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MeterError as err:
            raise UpdateFailed(str(err)) from err
        if not rows:
            raise UpdateFailed("sensor table is empty")
        now = time.monotonic()
        result: dict[str, Row] = {}
        for row in rows:
            if row.key in self.guarded:
                guard = self.guards.setdefault(row.key, MeterGuard())
                value = guard.check(row.value, row.unit, now)
                if value != row.value:
                    _LOGGER.debug("%s: implausible %s held back, keeping %s",
                                  row.key, row.value, value)
                    row = Row(row.key, row.label, row.prefix, row.obis, row.text, value, row.unit)
            result[row.key] = row
        return result
