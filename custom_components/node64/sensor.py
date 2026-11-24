from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROBLEM_STATES
from .coordinator import Node64Coordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Node64Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            Node64ChecksProblemCountSensor(coordinator, entry),
            Node64ChecksTotalSensor(coordinator, entry),
            Node64VersionSensor(coordinator, entry),
        ]
    )


class Node64Base(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        node = coordinator.data["status"]["node"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"node64 {node.get('name', '')}".strip(),
            manufacturer="ipv64.net",
            model="node64",
            sw_version=node.get("version"),
        )


class Node64ChecksProblemCountSensor(Node64Base):
    _attr_name = "Checks gestört"
    _attr_native_unit_of_measurement = "Checks"

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_checks_problem"

    @property
    def native_value(self) -> int:
        return sum(
            1
            for check in self.coordinator.data["checks"].values()
            if check.get("state", {}).get("state") in PROBLEM_STATES
        )


class Node64ChecksTotalSensor(Node64Base):
    _attr_name = "Checks gesamt"
    _attr_native_unit_of_measurement = "Checks"

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_checks_total"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data["checks"])


class Node64VersionSensor(Node64Base):
    _attr_name = "Version"

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_version"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data["status"]["node"].get("version")
