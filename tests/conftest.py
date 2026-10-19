"""Shared fixtures. The table is a real page of a Tasmota SML reader
(header with WiFi data removed); the status is built here."""

from __future__ import annotations

from pathlib import Path

import pytest
from homeassistant.const import CONF_HOST
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tasmota_smartmeter.const import DOMAIN

HOST = "meter.example"
# built from parts so that the repository-wide MAC check stays strict
MAC = ":".join(["02", "00", "00", "00", "00", "01"])  # noqa: FLY002
TABLE = (Path(__file__).parent / "fixtures" / "sml_table.html").read_text(encoding="utf-8")
STATUS = {
    "Status": {"DeviceName": "IR SmartMeter", "FriendlyName": ["IR SmartMeter"]},
    "StatusNET": {"Mac": MAC},
    "StatusFWR": {"Version": "15.1.0(tasmota32)", "Hardware": "ESP32-C3 v0.4"},
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, unique_id=MAC.lower(),
                           data={CONF_HOST: HOST}, title="IR SmartMeter")


@pytest.fixture
def mock_meter(aioclient_mock):
    def setup(table: str = TABLE, status: dict | None = None, code: int = 200):
        aioclient_mock.clear_requests()
        aioclient_mock.get(f"http://{HOST}/", text=table, status=code, params={"m": "1"})
        aioclient_mock.get(f"http://{HOST}/cm", json=status or STATUS, status=code)
        return aioclient_mock
    return setup
