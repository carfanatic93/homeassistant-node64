from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def check_device_info(entry: ConfigEntry, token: str, check: dict) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{token}")},
        via_device=(DOMAIN, entry.entry_id),
        name=check.get("name", token),
        model=check.get("type"),
    )
