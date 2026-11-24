import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Node64AuthError, Node64Client, Node64ConnectError
from .const import DOMAIN, SCAN_INTERVAL, STATS_INTERVAL, STATS_RANGES

_LOGGER = logging.getLogger(__name__)


class Node64Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: Node64Client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self._stats: dict[str, dict[str, Any]] = {}
        self._stats_at: float | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.client.status()
            checks = await self.client.checks()
            if self._stats_at is None or time.monotonic() - self._stats_at >= STATS_INTERVAL.total_seconds():
                self._stats = {
                    check["token"]: {
                        rng: await self.client.stats(check["token"], rng) for rng in STATS_RANGES
                    }
                    for check in checks
                }
                self._stats_at = time.monotonic()
        except Node64AuthError as err:
            raise ConfigEntryAuthFailed from err
        except Node64ConnectError as err:
            raise UpdateFailed(f"node64 nicht erreichbar: {err}") from err
        return {
            "status": status,
            "checks": {check["token"]: check for check in checks},
            "stats": self._stats,
            "proxy": await self._async_proxy(),
        }

    async def _async_proxy(self) -> dict[str, Any] | None:
        try:
            hosts = await self.client.cdn_hosts()
            stats = await self.client.cdn_stats()
            status = await self.client.cdn_status()
        except Node64ConnectError:
            return None
        return {
            "hosts": {host["id"]: host for host in hosts},
            "stats": stats.get("hosts", {}),
            "status": status,
        }
