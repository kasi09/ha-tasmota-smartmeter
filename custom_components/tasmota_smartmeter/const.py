"""Constants for the Tasmota Smart Meter integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "tasmota_smartmeter"
SCAN_INTERVAL: Final = timedelta(seconds=10)
TIMEOUT: Final = 8
# Tasmota's fixed user name for the web password
WEB_USER: Final = "admin"
