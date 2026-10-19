"""Sensors for Tasmota Smart Meter.

One sensor per numeric row of the Tasmota sensor table. Known OBIS codes get
a translated name and the right classes; unknown rows are classified by
their unit, so readers with other meter scripts work too.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.sensor.const import DEVICE_CLASS_UNITS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import MeterConfigEntry
from .const import DOMAIN
from .coordinator import MeterCoordinator
from .parser import Row

D = SensorDeviceClass
M = SensorStateClass.MEASUREMENT
TI = SensorStateClass.TOTAL_INCREASING


@dataclass(frozen=True)
class Kind:
    translation_key: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    enabled: bool = True


# OBIS (IEC 62056-61) codes commonly sent by smart meters.
OBIS: dict[str, Kind] = {
    "1.8.0": Kind("energy_import", D.ENERGY, TI),
    "2.8.0": Kind("energy_export", D.ENERGY, TI),
    "1.8.1": Kind("energy_import_t1", D.ENERGY, TI),
    "1.8.2": Kind("energy_import_t2", D.ENERGY, TI),
    "2.8.1": Kind("energy_export_t1", D.ENERGY, TI),
    "2.8.2": Kind("energy_export_t2", D.ENERGY, TI),
    "1.7.0": Kind("power_import", D.POWER, M),
    "2.7.0": Kind("power_export", D.POWER, M),
    "1.7.0-2.7.0": Kind("power_net", D.POWER, M),
    "16.7.0": Kind("power_net", D.POWER, M),
    "21.7.0": Kind("power_import_l1", D.POWER, M),
    "41.7.0": Kind("power_import_l2", D.POWER, M),
    "61.7.0": Kind("power_import_l3", D.POWER, M),
    "3.7.0": Kind("reactive_power_import", D.REACTIVE_POWER, M),
    "4.7.0": Kind("reactive_power_export", D.REACTIVE_POWER, M),
    "3.8.0": Kind("reactive_energy_import", D.REACTIVE_ENERGY, TI),
    "3.8.1": Kind("reactive_energy_import", D.REACTIVE_ENERGY, TI),
    "4.8.0": Kind("reactive_energy_export", D.REACTIVE_ENERGY, TI),
    "4.8.1": Kind("reactive_energy_export", D.REACTIVE_ENERGY, TI),
    "1.128.0": Kind("collection_energy", D.ENERGY, TI, enabled=False),
    "32.7.0": Kind("voltage_l1", D.VOLTAGE, M),
    "52.7.0": Kind("voltage_l2", D.VOLTAGE, M),
    "72.7.0": Kind("voltage_l3", D.VOLTAGE, M),
    "31.7.0": Kind("current_l1", D.CURRENT, M),
    "51.7.0": Kind("current_l2", D.CURRENT, M),
    "71.7.0": Kind("current_l3", D.CURRENT, M),
    "14.7.0": Kind("frequency", D.FREQUENCY, M),
    "13.7.0": Kind("power_factor", D.POWER_FACTOR, M),
}

# Units as Tasmota scripts write them -> Home Assistant spelling
UNITS = {"w": "W", "kw": "kW", "wh": "Wh", "kwh": "kWh", "mwh": "MWh", "v": "V",
         "a": "A", "hz": "Hz", "var": "var", "kvar": "kvar", "varh": "varh",
         "kvarh": "kvarh", "va": "VA", "kva": "kVA", "%": "%"}

BY_UNIT: dict[str, tuple[SensorDeviceClass, SensorStateClass]] = {
    "W": (D.POWER, M), "kW": (D.POWER, M),
    "Wh": (D.ENERGY, TI), "kWh": (D.ENERGY, TI), "MWh": (D.ENERGY, TI),
    "V": (D.VOLTAGE, M), "A": (D.CURRENT, M), "Hz": (D.FREQUENCY, M),
    "var": (D.REACTIVE_POWER, M), "kvar": (D.REACTIVE_POWER, M),
    "varh": (D.REACTIVE_ENERGY, TI), "kvarh": (D.REACTIVE_ENERGY, TI),
    "VA": (D.APPARENT_POWER, M), "kVA": (D.APPARENT_POWER, M),
}


def classify(row: Row) -> tuple[Kind, str | None]:
    """Classes and unit for a row. A unit that does not fit drops the class."""
    unit = UNITS.get((row.unit or "").lower(), row.unit)
    kind = OBIS.get(row.obis or "")
    if kind is None:
        dc, sc = BY_UNIT.get(unit or "", (None, M))
        kind = Kind(None, dc, sc)
    if kind.device_class and unit not in DEVICE_CLASS_UNITS.get(kind.device_class, set()):
        kind = Kind(None, None, M)
    return kind, unit


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeterConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    rows = list(coordinator.data.values())
    several_meters = len({r.prefix for r in rows if r.prefix}) > 1
    entities = []
    for row in rows:
        kind, unit = classify(row)
        if kind.state_class is TI:
            coordinator.guarded.add(row.key)
        entities.append(MeterSensor(coordinator, entry, row, kind, unit, several_meters))
    async_add_entities(entities)


class MeterSensor(CoordinatorEntity[MeterCoordinator], SensorEntity):
    """One value of the sensor table."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MeterCoordinator,
        entry: MeterConfigEntry,
        row: Row,
        kind: Kind,
        unit: str | None,
        several_meters: bool,
    ) -> None:
        super().__init__(coordinator)
        mac = format_mac(coordinator.status["mac"])
        self._key = row.key
        self._attr_unique_id = f"{mac}_{row.key}"
        self._attr_device_class = kind.device_class
        self._attr_state_class = kind.state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_registry_enabled_default = kind.enabled
        if kind.translation_key and not several_meters:
            self._attr_translation_key = kind.translation_key
        else:
            self._attr_name = row.label if several_meters else (row.text or row.label)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={(CONNECTION_NETWORK_MAC, mac)},
            name=coordinator.status["name"],
            manufacturer="Tasmota",
            model=coordinator.status.get("hardware"),
            sw_version=coordinator.status.get("firmware"),
            configuration_url=f"http://{entry.data['host']}",
        )

    @property
    def available(self) -> bool:
        return super().available and self._key in (self.coordinator.data or {})

    @property
    def native_value(self) -> float | None:
        row = (self.coordinator.data or {}).get(self._key)
        return row.value if row else None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        row = (self.coordinator.data or {}).get(self._key)
        return {"obis": row.obis, "label": row.label} if row else {}
