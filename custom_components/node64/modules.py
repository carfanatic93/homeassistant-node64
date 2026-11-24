from collections.abc import Callable
from typing import Any, NamedTuple

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import Node64Coordinator
from .entity import hub_id
from .i18n import parse_detail, translate
from .maintenance import m64_host_maintenance, m64_windows


class ModuleSensorDescription(NamedTuple):
    key: str
    name: str
    icon: str
    unit: str | None
    value_fn: Callable[[Any], Any]
    state_class: SensorStateClass | None = None


def m64_hosts(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    m64 = data.get("m64")
    return m64["hosts"] if m64 else {}


def m64_problems(data: dict[str, Any], uid: str) -> list[dict[str, Any]]:
    m64 = data.get("m64")
    return (m64.get("problems") or {}).get(uid, []) if m64 else []


def _problem_message(problem: dict[str, Any]) -> str:
    name = translate(problem.get("name") or "")
    detail = translate(problem.get("detail") or "")
    if name and detail:
        return f"{name}: {detail}"
    return name or detail or "Problem"


def problem_summary(problems: list[dict[str, Any]]) -> str:
    summary = "; ".join(_problem_message(p) for p in problems)
    return summary if len(summary) <= 250 else summary[:249] + "…"


def problem_attributes(problems: list[dict[str, Any]], host: dict[str, Any]) -> dict[str, Any]:
    return {
        "problems": [
            {
                "message": _problem_message(p),
                "severity": p.get("state"),
                "check": p.get("key") or None,
                "since": p.get("since") or None,
                "suppressed": bool(p.get("maint")),
                **parse_detail(p.get("detail")),
            }
            for p in problems
        ],
        "problem_summary": problem_summary(problems),
        "last_check_at": host.get("checked") or None,
    }


def _meter(host: dict[str, Any], label: str) -> Any:
    for meter in host.get("meters", []):
        if meter.get("label") == label:
            return meter.get("value")
    return None


def _hp_stats(hp: dict[str, Any]) -> dict[str, Any]:
    return (hp.get("stats") or {}) if hp else {}


def _hp_services(hp: dict[str, Any]) -> list[dict[str, Any]]:
    return ((hp.get("status") or {}).get("services")) or []


def _top_source(hp: dict[str, Any]) -> str | None:
    top = _hp_stats(hp).get("top_sources") or []
    return top[0]["key"] if top else None


def _m64_totals(hosts: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {
        "hosts": len(hosts),
        "problems": sum(int(h.get("problems", 0) or 0) for h in hosts.values()),
        "hosts_with_problems": sum(1 for h in hosts.values() if (h.get("problems") or 0) > 0),
    }


M64_HOST_SENSORS: tuple[ModuleSensorDescription, ...] = (
    ModuleSensorDescription("state", "Status", "mdi:heart-pulse", None, lambda h: h.get("state")),
    ModuleSensorDescription("problems", "Probleme", "mdi:alert-circle-outline", None, lambda h: h.get("problems")),
    ModuleSensorDescription("services", "Dienste", "mdi:format-list-bulleted", None, lambda h: h.get("services")),
    ModuleSensorDescription(
        "cpu", "CPU", "mdi:cpu-64-bit", "%", lambda h: _meter(h, "cpu"), SensorStateClass.MEASUREMENT
    ),
    ModuleSensorDescription(
        "ram", "RAM", "mdi:memory", "%", lambda h: _meter(h, "ram"), SensorStateClass.MEASUREMENT
    ),
)

M64_GLOBAL_SENSORS: tuple[ModuleSensorDescription, ...] = (
    ModuleSensorDescription("hosts", "Hosts", "mdi:server", None, lambda hosts: _m64_totals(hosts)["hosts"]),
    ModuleSensorDescription(
        "hosts_with_problems",
        "Hosts mit Problemen",
        "mdi:server-alert",
        None,
        lambda hosts: _m64_totals(hosts)["hosts_with_problems"],
    ),
    ModuleSensorDescription(
        "problems", "Probleme gesamt", "mdi:alert-circle-outline", None, lambda hosts: _m64_totals(hosts)["problems"]
    ),
)

HP_SENSORS: tuple[ModuleSensorDescription, ...] = (
    ModuleSensorDescription(
        "events_24h", "Ereignisse (24 h)", "mdi:shield-bug-outline", None,
        lambda hp: _hp_stats(hp).get("events"), SensorStateClass.MEASUREMENT,
    ),
    ModuleSensorDescription(
        "sources_24h", "Angreifer-IPs (24 h)", "mdi:ip-network", None,
        lambda hp: _hp_stats(hp).get("sources"), SensorStateClass.MEASUREMENT,
    ),
    ModuleSensorDescription(
        "logins_24h", "Login-Versuche (24 h)", "mdi:login", None,
        lambda hp: _hp_stats(hp).get("logins"), SensorStateClass.MEASUREMENT,
    ),
    ModuleSensorDescription(
        "services_listening", "Fallen-Dienste aktiv", "mdi:shield-check", None,
        lambda hp: sum(1 for s in _hp_services(hp) if s.get("listen")),
    ),
    ModuleSensorDescription("top_source", "Top-Angreifer", "mdi:target-account", None, _top_source),
    ModuleSensorDescription(
        "connections", "Verbindungen seit Start", "mdi:counter", None,
        lambda hp: ((hp.get("status") or {}).get("counters") or {}).get("connections"),
        SensorStateClass.TOTAL_INCREASING,
    ),
)


def m64_host_device(entry: ConfigEntry, uid: str, host: dict[str, Any], via: str | None) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_m64_{uid}")},
        via_device_id=via,
        name=host.get("name", uid),
        model=f"Monitor64 ({host.get('kind', 'host')})",
    )


def m64_global_device(entry: ConfigEntry, via: str | None) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_m64")},
        via_device_id=via,
        name="Monitor64",
        manufacturer="ipv64.net",
        model="Monitor64",
    )


def honeypot_device(entry: ConfigEntry, via: str | None) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_honeypot")},
        via_device_id=via,
        name="Honeypot64",
        manufacturer="ipv64.net",
        model="Honeypot64",
    )


class Node64M64HostSensor(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: Node64Coordinator, entry: ConfigEntry, uid: str, description: ModuleSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self._uid = uid
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_m64_{uid}_{description.key}"
        self._attr_device_info = m64_host_device(entry, uid, self._host, hub_id(self.coordinator, entry))
        self._attr_native_unit_of_measurement = description.unit
        self._attr_state_class = description.state_class

    @property
    def _host(self) -> dict[str, Any]:
        return m64_hosts(self.coordinator.data).get(self._uid, {})

    @property
    def available(self) -> bool:
        return super().available and self._uid in m64_hosts(self.coordinator.data)

    @property
    def native_value(self) -> Any:
        return self._description.value_fn(self._host)


class Node64M64GlobalSensor(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({"hosts"})

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry, description: ModuleSensorDescription) -> None:
        super().__init__(coordinator)
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_m64_{description.key}"
        self._attr_device_info = m64_global_device(entry, hub_id(self.coordinator, entry))
        self._attr_native_unit_of_measurement = description.unit
        self._attr_state_class = description.state_class

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("m64") is not None

    @property
    def native_value(self) -> Any:
        return self._description.value_fn(m64_hosts(self.coordinator.data))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._description.key not in ("problems", "hosts_with_problems"):
            return None
        data = self.coordinator.data
        windows = m64_windows(data)
        in_maintenance = {uid for uid, host in m64_hosts(data).items() if m64_host_maintenance(host, windows, uid)[0]}
        if self._description.key == "hosts_with_problems":
            counted = [uid for uid, host in m64_hosts(data).items() if host.get("problems")]
            attributes: dict[str, Any] = {
                "in_wartung": sum(1 for uid in counted if uid in in_maintenance),
                "ohne_wartung": sum(1 for uid in counted if uid not in in_maintenance),
            }
            return attributes
        hosts = []
        in_count = out_count = 0
        for uid, host in m64_hosts(data).items():
            problems = m64_problems(data, uid)
            count = int(host.get("problems") or 0)
            if uid in in_maintenance:
                in_count += count
            else:
                out_count += count
            if problems:
                hosts.append(
                    {
                        "host": host.get("name", uid),
                        "count": len(problems),
                        "problem_summary": problem_summary(problems),
                    }
                )
        return {"hosts": hosts, "in_wartung": in_count, "ohne_wartung": out_count}


class Node64HoneypotSensor(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry, description: ModuleSensorDescription) -> None:
        super().__init__(coordinator)
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_honeypot_{description.key}"
        self._attr_device_info = honeypot_device(entry, hub_id(self.coordinator, entry))
        self._attr_native_unit_of_measurement = description.unit
        self._attr_state_class = description.state_class

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("hp") is not None

    @property
    def native_value(self) -> Any:
        return self._description.value_fn(self.coordinator.data.get("hp") or {})


class Node64M64ProblemBinarySensor(CoordinatorEntity[Node64Coordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_name = "Probleme"
    _unrecorded_attributes = frozenset({"problems", "last_check_at"})

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry, uid: str) -> None:
        super().__init__(coordinator)
        self._uid = uid
        self._attr_unique_id = f"{entry.entry_id}_m64_{uid}_problem"
        self._attr_device_info = m64_host_device(entry, uid, self._host, hub_id(self.coordinator, entry))

    @property
    def _host(self) -> dict[str, Any]:
        return m64_hosts(self.coordinator.data).get(self._uid, {})

    @property
    def available(self) -> bool:
        return super().available and self._uid in m64_hosts(self.coordinator.data)

    @property
    def is_on(self) -> bool:
        return (self._host.get("problems") or 0) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        in_maintenance, until, reason = m64_host_maintenance(
            self._host, m64_windows(self.coordinator.data), self._uid
        )
        return {
            **problem_attributes(m64_problems(self.coordinator.data, self._uid), self._host),
            "maintenance": in_maintenance,
            "maintenance_until": until,
            "maintenance_reason": reason,
        }


class Node64HoneypotProblemBinarySensor(CoordinatorEntity[Node64Coordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_name = "Fallen-Dienst gestört"

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_honeypot_service_problem"
        self._attr_device_info = honeypot_device(entry, hub_id(self.coordinator, entry))

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("hp") is not None

    @property
    def is_on(self) -> bool:
        return any(not s.get("listen") for s in _hp_services(self.coordinator.data.get("hp") or {}))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "services": [
                {"service": s.get("service"), "port": s.get("port"), "listen": s.get("listen"), "error": s.get("error")}
                for s in _hp_services(self.coordinator.data.get("hp") or {})
            ]
        }
