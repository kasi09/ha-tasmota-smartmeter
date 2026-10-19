"""HTTP access to a Tasmota smart meter reader. Read-only."""

from __future__ import annotations

from typing import Any

import aiohttp

from .const import TIMEOUT, WEB_USER
from .parser import Row, parse_table


class MeterError(Exception):
    """The reader could not be reached or answered with an error."""


class MeterAuthError(MeterError):
    """The web password was rejected."""


class TasmotaMeterApi:
    """Reads the sensor table and the device status of one Tasmota device."""

    def __init__(self, session: aiohttp.ClientSession, host: str, password: str | None) -> None:
        self._session = session
        self._base = f"http://{host}"
        self._headers = (
            {"Authorization": aiohttp.encode_basic_auth(WEB_USER, password)} if password else {}
        )
        self._params = {"user": WEB_USER, "password": password} if password else {}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> aiohttp.ClientResponse:
        try:
            resp = await self._session.get(
                f"{self._base}{path}",
                params=params,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise MeterError(f"{path}: {err}") from err
        if resp.status != 200:
            resp.release()
            if resp.status == 401:
                raise MeterAuthError("web password rejected")
            raise MeterError(f"HTTP {resp.status} for {path}")
        return resp

    async def rows(self) -> list[Row]:
        resp = await self._get("/", {"m": "1"})
        try:
            return parse_table(await resp.text())
        except (aiohttp.ClientError, UnicodeDecodeError) as err:
            raise MeterError(str(err)) from err

    async def status(self) -> dict[str, Any]:
        """Name, MAC, firmware and hardware - nothing else is kept."""
        resp = await self._get("/cm", {"cmnd": "Status 0", **self._params})
        try:
            data = await resp.json(content_type=None)
        except (aiohttp.ClientError, ValueError) as err:
            raise MeterError(str(err)) from err
        if not isinstance(data, dict) or "WARNING" in data:
            raise MeterAuthError("web password required")
        status, net, fw = data.get("Status", {}), data.get("StatusNET", {}), data.get("StatusFWR", {})
        if not net.get("Mac"):
            raise MeterError("no MAC address in Status 0")
        return {
            "name": status.get("DeviceName") or (status.get("FriendlyName") or ["Tasmota"])[0],
            "mac": net["Mac"],
            "firmware": fw.get("Version"),
            "hardware": fw.get("Hardware"),
        }
