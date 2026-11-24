from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def subentry_id(entry: ConfigEntry, subentry_type: str) -> str | None:
    return next(
        (sid for sid, sub in entry.subentries.items() if sub.subentry_type == subentry_type),
        None,
    )


def check_device_info(entry: ConfigEntry, token: str, check: dict) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{token}")},
        via_device=(DOMAIN, entry.entry_id),
        name=check.get("name", token),
        model=check.get("type"),
    )
