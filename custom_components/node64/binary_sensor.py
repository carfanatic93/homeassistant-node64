from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROBLEM_STATES, SUB_HEALTHCHECKS, SUB_HONEYPOT, SUB_MONITOR64, SUB_PROXY64
from .coordinator import Node64Coordinator
from .entity import check_device_info, subentry_id
from .maintenance import hc_maintenance_for, m64_host_maintenance, m64_windows, maintenance_windows
from .modules import Node64HoneypotProblemBinarySensor, Node64M64ProblemBinarySensor, m64_hosts
from .proxy import Node64ProxyReachBinarySensor, proxy_hosts


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: Node64Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Node64MaintenanceActiveBinarySensor(coordinator, entry)])

    hc_id = subentry_id(entry, SUB_HEALTHCHECKS)
    if hc_id:
        known_checks: set[str] = set()

        @callback
        def _add_checks() -> None:
            new = [
                Node64CheckBinarySensor(coordinator, entry, token)
                for token in coordinator.data["checks"]
                if token not in known_checks
            ]
            known_checks.update(coordinator.data["checks"])
            if new:
                async_add_entities(new, config_subentry_id=hc_id)

        _add_checks()
        entry.async_on_unload(coordinator.async_add_listener(_add_checks))

    px_id = subentry_id(entry, SUB_PROXY64)
    if px_id:
        known_hosts: set[int] = set()

        @callback
        def _add_proxy_reach() -> None:
            if coordinator.data.get("proxy") is None:
                return
            new = [
                Node64ProxyReachBinarySensor(coordinator, entry, host_id)
                for host_id in proxy_hosts(coordinator.data)
                if host_id not in known_hosts
            ]
            known_hosts.update(proxy_hosts(coordinator.data))
            if new:
                async_add_entities(new, config_subentry_id=px_id)

        _add_proxy_reach()
        entry.async_on_unload(coordinator.async_add_listener(_add_proxy_reach))

    m64_id = subentry_id(entry, SUB_MONITOR64)
    if m64_id:
        known_m64: set[str] = set()

        @callback
        def _add_m64_problems() -> None:
            if coordinator.data.get("m64") is None:
                return
            new = [
                Node64M64ProblemBinarySensor(coordinator, entry, uid)
                for uid in m64_hosts(coordinator.data)
                if uid not in known_m64
            ]
            known_m64.update(m64_hosts(coordinator.data))
            if new:
                async_add_entities(new, config_subentry_id=m64_id)

        _add_m64_problems()
        entry.async_on_unload(coordinator.async_add_listener(_add_m64_problems))

    hp_id = subentry_id(entry, SUB_HONEYPOT)
    if hp_id:
        hp_added = False

        @callback
        def _add_hp_problem() -> None:
            nonlocal hp_added
            if hp_added or coordinator.data.get("hp") is None:
                return
            hp_added = True
            async_add_entities([Node64HoneypotProblemBinarySensor(coordinator, entry)], config_subentry_id=hp_id)

        _add_hp_problem()
        entry.async_on_unload(coordinator.async_add_listener(_add_hp_problem))


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
        until, reason = hc_maintenance_for(self.coordinator.data, self._token)
        return {
            "check_type": check.get("type"),
            "target": check.get("target"),
            "state": state.get("state"),
            "since": state.get("since"),
            "last_check_at": state.get("last_check_at"),
            "last_reason": state.get("last_reason"),
            "last_message": state.get("last_message"),
            "maintenance": state.get("maintenance", False),
            "maintenance_until": until,
            "maintenance_reason": reason,
            "paused": check.get("paused", False),
            "tags": check.get("tags", []),
        }


class Node64MaintenanceActiveBinarySensor(CoordinatorEntity[Node64Coordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Wartung aktiv"
    _unrecorded_attributes = frozenset({"windows"})

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_maintenance_active"
        node = coordinator.data["status"]["node"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"node64 {node.get('name', '')}".strip(),
            manufacturer="ipv64.net",
            model="node64",
            sw_version=node.get("version"),
        )

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        windows = m64_windows(data)
        return bool(maintenance_windows(data)) or any(
            m64_host_maintenance(host, windows, uid)[0] for uid, host in m64_hosts(data).items()
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"windows": maintenance_windows(self.coordinator.data)}
