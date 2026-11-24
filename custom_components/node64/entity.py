from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def subentry_id(entry: ConfigEntry, module: str) -> str | None:
    return next(
        (
            sid
            for sid, sub in entry.subentries.items()
            if sub.data.get("module") == module or sub.subentry_type == module
        ),
        None,
    )


def check_device_info(entry: ConfigEntry, token: str, check: dict) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{token}")},
        via_device=(DOMAIN, entry.entry_id),
        name=check.get("name", token),
        model=check.get("type"),
    )
