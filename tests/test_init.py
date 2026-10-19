"""Config flow, setup, sensor classes, guard in the coordinator, diagnostics."""

import json

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.tasmota_smartmeter.const import DOMAIN
from custom_components.tasmota_smartmeter.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import HOST, MAC, TABLE


async def setup(hass, entry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def state(hass, key: str):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{MAC.lower()}_{key}")
    assert entity_id, key
    return hass.states.get(entity_id)


async def test_flow_success(hass: HomeAssistant, mock_meter) -> None:
    mock_meter()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "IR SmartMeter"
    assert result["result"].unique_id == MAC.lower()
    await hass.async_block_till_done()


async def test_flow_errors(hass: HomeAssistant, mock_meter, aioclient_mock) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    mock_meter(code=401)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["errors"] == {"base": "invalid_auth"}
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"http://{HOST}/cm", exc=TimeoutError)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["errors"] == {"base": "cannot_connect"}
    mock_meter(table="<html>no table</html>")
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_HOST: HOST})
    assert result["errors"] == {"base": "no_meter_data"}


async def test_password_sent(hass: HomeAssistant, mock_meter, config_entry) -> None:
    mock = mock_meter()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: HOST, CONF_PASSWORD: "geheim-nur-test"}
    )
    cm = next(c for c in mock.mock_calls if c[1].path == "/cm")
    assert cm[1].query["password"] == "geheim-nur-test"
    assert cm[3]["Authorization"].startswith("Basic ")
    await hass.async_block_till_done()


async def test_sensors_and_classes(hass: HomeAssistant, mock_meter, config_entry) -> None:
    mock_meter()
    await setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    s = state(hass, "z1_1_8_0")
    assert s.attributes["device_class"] == "energy"
    assert s.attributes["state_class"] == "total_increasing"
    assert s.attributes["unit_of_measurement"] == "kWh"
    assert s.attributes["obis"] == "1.8.0"
    assert float(s.state) > 39000
    s = state(hass, "z1_3_8_1")
    assert s.attributes["device_class"] == "reactive_energy"
    s = state(hass, "z1_1_7_0_minus_2_7_0")
    assert s.attributes["device_class"] == "power" and float(s.state) < 0
    reg = er.async_get(hass)
    entry = reg.async_get(reg.async_get_entity_id("sensor", DOMAIN, f"{MAC.lower()}_z1_1_128_0"))
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_reader_reboot_does_not_reset_statistics(hass, mock_meter, config_entry) -> None:
    mock_meter()
    await setup(hass, config_entry)
    coordinator = config_entry.runtime_data
    await coordinator.async_refresh()                    # baseline through the guard
    before = float(state(hass, "z1_1_8_0").state)
    mock_meter(table=TABLE.replace("39717.090 kWh", "0.000 kWh"))
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert float(state(hass, "z1_1_8_0").state) == before


async def test_reader_offline_unavailable(hass, mock_meter, aioclient_mock, config_entry) -> None:
    mock_meter()
    await setup(hass, config_entry)
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"http://{HOST}/", exc=TimeoutError, params={"m": "1"})
    await config_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert state(hass, "z1_1_8_0").state == "unavailable"


async def test_diagnostics_redacts_password(hass, mock_meter) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_meter()
    entry = MockConfigEntry(domain=DOMAIN, unique_id=MAC.lower(),
                            data={CONF_HOST: HOST, CONF_PASSWORD: "geheim-nur-test"})
    await setup(hass, entry)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert "geheim-nur-test" not in json.dumps(diag)
    assert len(diag["rows"]) == 10


async def test_unload(hass, mock_meter, config_entry) -> None:
    mock_meter()
    await setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
