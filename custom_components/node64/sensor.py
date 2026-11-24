from collections.abc import Callable
from typing import Any, NamedTuple

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROBLEM_STATES
from .coordinator import Node64Coordinator
from .entity import check_device_info


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

    known: set[str] = set()

    @callback
    def _add_new_checks() -> None:
        new = [
            Node64CheckSensor(coordinator, entry, token, description)
            for token in coordinator.data["checks"]
            if token not in known
            for description in CHECK_SENSORS
        ]
        known.update(coordinator.data["checks"])
        if new:
            async_add_entities(new)

    _add_new_checks()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_checks))


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


class Node64SensorDescription(NamedTuple):
    key: str
    name: str
    icon: str
    unit: str | None
    value_fn: Callable[[dict[str, Any], dict[str, Any]], Any]
    diagnostic: bool = False


def _state(check: dict[str, Any]) -> dict[str, Any]:
    return check.get("state", {})


def _range(stats: dict[str, Any], rng: str) -> dict[str, Any]:
    return stats.get(rng, {})


CHECK_SENSORS: tuple[Node64SensorDescription, ...] = (
    Node64SensorDescription("status", "Status", "mdi:lan-connect", None, lambda c, s: _state(c).get("state")),
    Node64SensorDescription(
        "latency", "Antwortzeit", "mdi:clock-fast", "ms", lambda c, s: _state(c).get("last_latency_ms")
    ),
    Node64SensorDescription(
        "latency_24h", "Antwortzeit Ø (1 Tag)", "mdi:clock-fast", "ms", lambda c, s: _range(s, "24h").get("avg_ms")
    ),
    Node64SensorDescription(
        "latency_30d", "Antwortzeit Ø (30 Tage)", "mdi:clock-fast", "ms", lambda c, s: _range(s, "30d").get("avg_ms")
    ),
    Node64SensorDescription(
        "latency_1y", "Antwortzeit Ø (365 Tage)", "mdi:clock-fast", "ms", lambda c, s: _range(s, "1y").get("avg_ms")
    ),
    Node64SensorDescription(
        "uptime_24h", "Verfügbarkeit (1 Tag)", "mdi:history", "%", lambda c, s: _range(s, "24h").get("up_percent")
    ),
    Node64SensorDescription(
        "uptime_30d", "Verfügbarkeit (30 Tage)", "mdi:history", "%", lambda c, s: _range(s, "30d").get("up_percent")
    ),
    Node64SensorDescription(
        "uptime_1y", "Verfügbarkeit (365 Tage)", "mdi:history", "%", lambda c, s: _range(s, "1y").get("up_percent")
    ),
    Node64SensorDescription(
        "target", "Ziel", "mdi:ip-network", None, lambda c, s: c.get("target"), diagnostic=True
    ),
    Node64SensorDescription(
        "type", "Typ", "mdi:signal-variant", None, lambda c, s: c.get("type"), diagnostic=True
    ),
)


class Node64CheckSensor(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Node64Coordinator,
        entry: ConfigEntry,
        token: str,
        description: Node64SensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self._token = token
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_check_{token}_{description.key}"
        self._attr_device_info = check_device_info(entry, token, self._check)
        self._attr_native_unit_of_measurement = description.unit
        if description.unit:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if description.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def _check(self) -> dict[str, Any]:
        return self.coordinator.data["checks"].get(self._token, {})

    @property
    def available(self) -> bool:
        return super().available and self._token in self.coordinator.data["checks"]

    @property
    def native_value(self) -> Any:
        stats = self.coordinator.data["stats"].get(self._token, {})
        return self._description.value_fn(self._check, stats)
