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


class ProxyDescription(NamedTuple):
    key: str
    name: str
    icon: str
    unit: str | None
    value_fn: Callable[[dict[str, Any], dict[str, Any]], Any]


def _reach(host: dict[str, Any]) -> dict[str, Any]:
    return host.get("reach", {})


def _cert(host: dict[str, Any]) -> dict[str, Any]:
    return host.get("certificate", {})


def _stat(stat: dict[str, Any], key: str) -> Any:
    return stat.get(key)


def _reach_ms(host: dict[str, Any], stat: dict[str, Any]) -> Any:
    return _reach(host).get("ms") if _reach(host).get("state") in ("up", "slow") else None


PROXY_SENSORS: tuple[ProxyDescription, ...] = (
    ProxyDescription("reach", "Erreichbarkeit", "mdi:lan-connect", None, lambda h, s: _reach(h).get("state")),
    ProxyDescription("reach_ms", "Antwortzeit", "mdi:clock-fast", "ms", _reach_ms),
    ProxyDescription("cert_days", "Zertifikat gültig", "mdi:certificate", "d", lambda h, s: _cert(h).get("days_left")),
    ProxyDescription("requests_24h", "Anfragen (24 h)", "mdi:web", None, lambda h, s: _stat(s, "requests")),
    ProxyDescription("errors_24h", "Fehler 5xx (24 h)", "mdi:alert-circle-outline", None, lambda h, s: _stat(s, "5xx")),
    ProxyDescription("blocked_24h", "Abgewiesen (24 h)", "mdi:shield-alert-outline", None, lambda h, s: _stat(s, "blocked")),
)


def _sum(stats: dict[str, dict[str, Any]], key: str) -> int:
    return sum(int(s.get(key, 0) or 0) for s in stats.values())


CDN_SENSORS: tuple[ProxyDescription, ...] = (
    ProxyDescription("hosts", "Hosts", "mdi:server-network", None, lambda st, s: st.get("hosts")),
    ProxyDescription("targets_down", "Ziele gestört", "mdi:server-network-off", None, lambda st, s: st.get("targets_down")),
    ProxyDescription("requests_24h", "Anfragen (24 h)", "mdi:web", None, lambda st, s: _sum(s, "requests")),
    ProxyDescription("errors_24h", "Fehler 5xx (24 h)", "mdi:alert-circle-outline", None, lambda st, s: _sum(s, "5xx")),
    ProxyDescription("blocked_24h", "Abgewiesen (24 h)", "mdi:shield-alert-outline", None, lambda st, s: _sum(s, "blocked")),
)


def proxy_device_info(entry: ConfigEntry, host_id: int, host: dict[str, Any], via: str | None) -> DeviceInfo:
    names = host.get("names") or [str(host_id)]
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_proxy_{host_id}")},
        via_device_id=via,
        name=names[0],
        model=f"Proxy-Host ({host.get('kind', 'proxy')})",
    )


def cdn_device_info(entry: ConfigEntry, via: str | None) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_cdn64")},
        via_device_id=via,
        name="CDN64",
        manufacturer="ipv64.net",
        model="Proxy64 / CDN64",
    )


def proxy_hosts(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    proxy = data.get("proxy")
    return proxy["hosts"] if proxy else {}


class Node64ProxySensor(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: Node64Coordinator,
        entry: ConfigEntry,
        host_id: int,
        description: ProxyDescription,
    ) -> None:
        super().__init__(coordinator)
        self._host_id = host_id
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_proxy_{host_id}_{description.key}"
        self._attr_device_info = proxy_device_info(entry, host_id, self._host, hub_id(self.coordinator, entry))
        self._attr_native_unit_of_measurement = description.unit
        if description.unit in ("ms", "d"):
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def _host(self) -> dict[str, Any]:
        return proxy_hosts(self.coordinator.data).get(self._host_id, {})

    @property
    def _stat(self) -> dict[str, Any]:
        return self.coordinator.data["proxy"]["stats"].get(str(self._host_id), {})

    @property
    def available(self) -> bool:
        return super().available and self._host_id in proxy_hosts(self.coordinator.data)

    @property
    def native_value(self) -> Any:
        return self._description.value_fn(self._host, self._stat)


class Node64CdnSensor(CoordinatorEntity[Node64Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry, description: ProxyDescription) -> None:
        super().__init__(coordinator)
        self._description = description
        self._attr_name = description.name
        self._attr_icon = description.icon
        self._attr_unique_id = f"{entry.entry_id}_cdn64_{description.key}"
        self._attr_device_info = cdn_device_info(entry, hub_id(self.coordinator, entry))
        self._attr_native_unit_of_measurement = description.unit

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("proxy") is not None

    @property
    def native_value(self) -> Any:
        proxy = self.coordinator.data.get("proxy") or {}
        return self._description.value_fn(proxy.get("status", {}), proxy.get("stats", {}))


class Node64ProxyReachBinarySensor(CoordinatorEntity[Node64Coordinator], BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_name = "Erreichbarkeit gestört"

    def __init__(self, coordinator: Node64Coordinator, entry: ConfigEntry, host_id: int) -> None:
        super().__init__(coordinator)
        self._host_id = host_id
        self._attr_unique_id = f"{entry.entry_id}_proxy_{host_id}_reach_problem"
        self._attr_device_info = proxy_device_info(entry, host_id, self._host, hub_id(self.coordinator, entry))

    @property
    def _host(self) -> dict[str, Any]:
        return proxy_hosts(self.coordinator.data).get(self._host_id, {})

    @property
    def available(self) -> bool:
        return super().available and self._host_id in proxy_hosts(self.coordinator.data)

    @property
    def is_on(self) -> bool:
        return _reach(self._host).get("state") == "down"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        reach = _reach(self._host)
        return {"error": reach.get("error"), "checked_at": reach.get("checked_at")}
