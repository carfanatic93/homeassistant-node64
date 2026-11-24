from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROBLEM_STATES, SUB_HEALTHCHECKS, SUB_HONEYPOT, SUB_MONITOR64, SUB_PROXY64
from .coordinator import Node64Coordinator
from .entity import subentry_id
from .modules import (
    HP_SENSORS,
    M64_GLOBAL_SENSORS,
    M64_HOST_SENSORS,
    Node64HoneypotSensor,
    Node64M64GlobalSensor,
    Node64M64HostSensor,
    m64_hosts,
)
from .proxy import CDN_SENSORS, PROXY_SENSORS, Node64CdnSensor, Node64ProxySensor, proxy_hosts
from .sensors_check import CHECK_SENSORS, Node64CheckSensor


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

    hc_id = subentry_id(entry, SUB_HEALTHCHECKS)
    if hc_id:
        known_checks: set[str] = set()

        @callback
        def _add_checks() -> None:
            new = [
                Node64CheckSensor(coordinator, entry, token, description)
                for token in coordinator.data["checks"]
                if token not in known_checks
                for description in CHECK_SENSORS
            ]
            known_checks.update(coordinator.data["checks"])
            if new:
                async_add_entities(new, config_subentry_id=hc_id)

        _add_checks()
        entry.async_on_unload(coordinator.async_add_listener(_add_checks))

    px_id = subentry_id(entry, SUB_PROXY64)
    if px_id:
        cdn_added = False
        known_hosts: set[int] = set()

        @callback
        def _add_proxy() -> None:
            nonlocal cdn_added
            if coordinator.data.get("proxy") is None:
                return
            new: list[SensorEntity] = []
            if not cdn_added:
                cdn_added = True
                new.extend(Node64CdnSensor(coordinator, entry, d) for d in CDN_SENSORS)
            for host_id in proxy_hosts(coordinator.data):
                if host_id not in known_hosts:
                    known_hosts.add(host_id)
                    new.extend(Node64ProxySensor(coordinator, entry, host_id, d) for d in PROXY_SENSORS)
            if new:
                async_add_entities(new, config_subentry_id=px_id)

        _add_proxy()
        entry.async_on_unload(coordinator.async_add_listener(_add_proxy))

    m64_id = subentry_id(entry, SUB_MONITOR64)
    if m64_id:
        m64_global_added = False
        known_m64: set[str] = set()

        @callback
        def _add_m64() -> None:
            nonlocal m64_global_added
            if coordinator.data.get("m64") is None:
                return
            new: list[SensorEntity] = []
            if not m64_global_added:
                m64_global_added = True
                new.extend(Node64M64GlobalSensor(coordinator, entry, d) for d in M64_GLOBAL_SENSORS)
            for uid in m64_hosts(coordinator.data):
                if uid not in known_m64:
                    known_m64.add(uid)
                    new.extend(Node64M64HostSensor(coordinator, entry, uid, d) for d in M64_HOST_SENSORS)
            if new:
                async_add_entities(new, config_subentry_id=m64_id)

        _add_m64()
        entry.async_on_unload(coordinator.async_add_listener(_add_m64))

    hp_id = subentry_id(entry, SUB_HONEYPOT)
    if hp_id:
        hp_added = False

        @callback
        def _add_hp() -> None:
            nonlocal hp_added
            if hp_added or coordinator.data.get("hp") is None:
                return
            hp_added = True
            async_add_entities(
                [Node64HoneypotSensor(coordinator, entry, d) for d in HP_SENSORS],
                config_subentry_id=hp_id,
            )

        _add_hp()
        entry.async_on_unload(coordinator.async_add_listener(_add_hp))


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

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        problem = [
            check
            for check in self.coordinator.data["checks"].values()
            if check.get("state", {}).get("state") in PROBLEM_STATES
        ]
        in_maintenance = sum(1 for check in problem if check.get("state", {}).get("maintenance"))
        return {"in_wartung": in_maintenance, "ohne_wartung": len(problem) - in_maintenance}


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
