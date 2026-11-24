import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Node64AuthError, Node64Client, Node64ConnectError
from .const import DOMAIN, SCAN_INTERVAL

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

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.client.status()
            checks = await self.client.checks()
        except Node64AuthError as err:
            raise ConfigEntryAuthFailed from err
        except Node64ConnectError as err:
            raise UpdateFailed(f"node64 nicht erreichbar: {err}") from err
        return {
            "status": status,
            "checks": {check["token"]: check for check in checks},
        }
