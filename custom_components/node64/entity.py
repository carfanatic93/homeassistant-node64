from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def hub_id(coordinator: Any, entry: ConfigEntry) -> str | None:
    device = dr.async_get(coordinator.hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    return device.id if device else None


def subentry_id(entry: ConfigEntry, module: str) -> str | None:
    return next(
        (
            sid
            for sid, sub in entry.subentries.items()
            if sub.data.get("module") == module or sub.subentry_type == module
        ),
        None,
    )


def check_device_info(entry: ConfigEntry, token: str, check: dict, via: str | None) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{token}")},
        via_device_id=via,
        name=check.get("name", token),
        model=check.get("type"),
    )
