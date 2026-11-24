from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROBLEM_STATES
from .coordinator import Node64Coordinator
from .entity import check_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Node64Coordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add_new_checks() -> None:
        new = [
            Node64CheckBinarySensor(coordinator, entry, token)
            for token in coordinator.data["checks"]
            if token not in known
        ]
        known.update(coordinator.data["checks"])
        if new:
            async_add_entities(new)

    _add_new_checks()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_checks))


class Node64CheckBinarySensor(CoordinatorEntity[Node64Coordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry, token: str) -> None:
        super().__init__(coordinator)
        self._token = token
        self._attr_unique_id = f"{entry.entry_id}_check_{token}"
        self._attr_device_info = check_device_info(entry, token, self._check)

    @property
    def _check(self) -> dict:
        return self.coordinator.data["checks"].get(self._token, {})

    @property
    def available(self) -> bool:
        return super().available and self._token in self.coordinator.data["checks"]

    @property
    def is_on(self) -> bool:
        return self._check.get("state", {}).get("state") in PROBLEM_STATES

    @property
    def extra_state_attributes(self) -> dict:
        check = self._check
        state = check.get("state", {})
        return {
            "check_type": check.get("type"),
            "target": check.get("target"),
            "state": state.get("state"),
            "since": state.get("since"),
            "last_check_at": state.get("last_check_at"),
            "last_reason": state.get("last_reason"),
            "last_message": state.get("last_message"),
            "maintenance": state.get("maintenance", False),
            "paused": check.get("paused", False),
            "tags": check.get("tags", []),
        }
