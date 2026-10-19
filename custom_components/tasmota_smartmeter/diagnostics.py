"""Diagnostics: device status and the parsed rows, password redacted."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant

from . import MeterConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MeterConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), {CONF_PASSWORD}),
        "status": coordinator.status,
        "rows": [asdict(r) for r in (coordinator.data or {}).values()],
        "guard_rejections": {k: g.rejected for k, g in coordinator.guards.items()},
    }
